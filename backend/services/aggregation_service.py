"""
services/aggregation_service.py — AggregationService (item 4.1, Etapa 4).

Única pieza autorizada a construir queries de agregación sobre el
estado del sistema. Ver DECISION_LOG.md, ADR "ningún dashboard consulta
la base de datos o los motores directamente": el flujo obligatorio es
Dashboard → DashboardService → AggregationService → Motores/DB.

Las funciones que ya existían en dashboard_service.py y eran, en
esencia, agregaciones (obtener_stats, tendencia_diaria,
distribucion_scores_por_banco, top_hashes_reutilizados) se movieron
aquí sin cambiar su lógica -- dashboard_service.py ahora las expone
como wrappers delgados que llaman a este servicio.

FIX (2026-07): se encontró un bug real al agregar resumen-ejecutivo
(item 4.2) -- comparar Analisis.fecha (TIMESTAMP) contra un string
plano ('2026-07-05') hace que SQLAlchemy tipe el parámetro como VARCHAR
en vez de fecha, y Postgres rechaza la comparación
(UndefinedFunction: operator does not exist: timestamp >= character
varying). Este mismo patrón ya existía en
dashboard_service._construir_filtros_analisis() desde el ítem 2.1
(filtro de fecha del Historial) -- probablemente nunca se disparó de
forma visible porque nadie forzó ese filtro con valores reales lo
suficiente. _parsear_fecha() corrige esto en ambos archivos.

También se corrige un segundo bug, más sutil, en la misma revisión:
`fecha_hasta` comparado con `<=` excluye registros del mismo día
después de la medianoche (comparación de timestamp contra fecha pura a
las 00:00:00). Se corrige usando "antes del día siguiente" para
incluir el día completo.

Gaps conocidos, deliberadamente NO resueltos en este corte (ver
DECISION_LOG.md):
  - "Tiempo promedio de validación" -- requeriría persistir una
    duración por análisis en `analisis` (columna nueva); hoy
    metrics_service solo tiene un promedio en memoria del proceso.
  - "Actividad por empresa" (comparar múltiples empresas) -- sin
    sentido real hasta que exista autenticación multiempresa (Etapa 6).
"""
import datetime
from sqlalchemy import select, func, desc
from models.analisis import Analisis
from models.hash_documento import HashDocumento
from models.alerta import Alerta
from database import get_db_session, DEFAULT_EMPRESA_ID


def _parsear_fecha(valor: str | None) -> datetime.date | None:
    """
    Convierte un string de fecha ('2026-07-05') a un objeto date de
    Python antes de compararlo contra Analisis.fecha. Si el string no
    es parseable, devuelve None -- se ignora el filtro en vez de romper
    la consulta completa por un dato malformado (degradación con
    gracia, mismo criterio que el resto del sistema).
    """
    if not valor:
        return None
    try:
        return datetime.date.fromisoformat(valor.strip())
    except (ValueError, AttributeError):
        return None


def _filtro_rango_fechas(fecha_desde: str | None, fecha_hasta: str | None) -> list:
    """
    Construye las condiciones de rango de fecha para Analisis.fecha,
    ya con el fix de tipos y el fix de "día completo" aplicados.
    """
    condiciones = []
    fd = _parsear_fecha(fecha_desde)
    fh = _parsear_fecha(fecha_hasta)
    if fd:
        condiciones.append(Analisis.fecha >= fd)
    if fh:
        # "< día siguiente" en vez de "<= fh" -- incluye todo el día,
        # no solo el instante 00:00:00 de fh.
        condiciones.append(Analisis.fecha < (fh + datetime.timedelta(days=1)))
    return condiciones


# ─────────────────────────────────────────────────────────────────
# Movidas desde dashboard_service.py, con el fix de fechas aplicado.
# ─────────────────────────────────────────────────────────────────

def calcular_stats_generales(empresa_id: str = DEFAULT_EMPRESA_ID, fecha_desde: str | None = None, fecha_hasta: str | None = None) -> dict:
    """Métricas generales: total, hoy, score promedio, distribución por riesgo, documentos únicos/reutilizados."""
    with get_db_session() as db:
        if db is None:
            return {
                "total_analisis": 0, "analisis_hoy": 0, "score_promedio": None,
                "distribucion_riesgo": [], "documentos_unicos": 0, "documentos_reutilizados": 0,
            }

        base_filtro = [Analisis.empresa_id == empresa_id, Analisis.deleted_at.is_(None)]
        base_filtro.extend(_filtro_rango_fechas(fecha_desde, fecha_hasta))

        total = db.execute(select(func.count(Analisis.id)).where(*base_filtro)).scalar() or 0

        hoy = datetime.date.today()
        analisis_hoy = db.execute(
            select(func.count(Analisis.id)).where(
                Analisis.empresa_id == empresa_id,
                Analisis.deleted_at.is_(None),
                func.date(Analisis.fecha) == hoy,
            )
        ).scalar() or 0

        score_promedio = db.execute(select(func.avg(Analisis.score_final)).where(*base_filtro)).scalar()

        distribucion_rows = db.execute(
            select(Analisis.riesgo, func.count(Analisis.id))
            .where(*base_filtro)
            .group_by(Analisis.riesgo)
        ).all()
        distribucion_riesgo = [{"riesgo": r or "INDETERMINADO", "total": c} for r, c in distribucion_rows]

        documentos_unicos = db.execute(
            select(func.count(HashDocumento.id)).where(
                HashDocumento.empresa_id == empresa_id,
                HashDocumento.deleted_at.is_(None),
            )
        ).scalar() or 0

        documentos_reutilizados = db.execute(
            select(func.count(HashDocumento.id)).where(
                HashDocumento.empresa_id == empresa_id,
                HashDocumento.deleted_at.is_(None),
                HashDocumento.veces_visto > 1,
            )
        ).scalar() or 0

        return {
            "total_analisis": total,
            "analisis_hoy": analisis_hoy,
            "score_promedio": round(float(score_promedio), 2) if score_promedio is not None else None,
            "distribucion_riesgo": distribucion_riesgo,
            "documentos_unicos": documentos_unicos,
            "documentos_reutilizados": documentos_reutilizados,
        }


def calcular_tendencia_diaria(empresa_id: str = DEFAULT_EMPRESA_ID, dias: int = 30) -> list:
    """Serie diaria de totales y score promedio."""
    with get_db_session() as db:
        if db is None:
            return []

        desde = datetime.date.today() - datetime.timedelta(days=dias)

        rows = db.execute(
            select(
                func.date(Analisis.fecha).label("dia"),
                func.count(Analisis.id),
                func.avg(Analisis.score_final),
            )
            .where(
                Analisis.empresa_id == empresa_id,
                Analisis.deleted_at.is_(None),
                Analisis.fecha >= desde,
            )
            .group_by(func.date(Analisis.fecha))
            .order_by(func.date(Analisis.fecha))
        ).all()

        return [
            {
                "fecha": dia.isoformat() if hasattr(dia, "isoformat") else str(dia),
                "total": total,
                "score_promedio": round(float(score_avg), 2) if score_avg is not None else None,
            }
            for dia, total, score_avg in rows
        ]


def calcular_distribucion_scores_por_banco(empresa_id: str = DEFAULT_EMPRESA_ID, dias: int = 30, min_analisis: int = 1) -> list:
    """Distribución de scores de Claude Vision por banco (item 1.6)."""
    with get_db_session() as db:
        if db is None:
            return []

        desde = datetime.date.today() - datetime.timedelta(days=dias)

        rows = db.execute(
            select(
                Analisis.banco_detectado,
                func.count(Analisis.id),
                func.avg(Analisis.score_claude),
                func.avg(Analisis.score_final),
            )
            .where(
                Analisis.empresa_id == empresa_id,
                Analisis.deleted_at.is_(None),
                Analisis.fecha >= desde,
                Analisis.banco_detectado.is_not(None),
            )
            .group_by(Analisis.banco_detectado)
            .having(func.count(Analisis.id) >= min_analisis)
            .order_by(desc(func.count(Analisis.id)))
        ).all()

        return [
            {
                "banco": banco,
                "total_analisis": total,
                "score_claude_promedio": round(float(score_claude_avg), 2) if score_claude_avg is not None else None,
                "score_final_promedio": round(float(score_final_avg), 2) if score_final_avg is not None else None,
            }
            for banco, total, score_claude_avg, score_final_avg in rows
        ]


def calcular_top_hashes_reutilizados(empresa_id: str = DEFAULT_EMPRESA_ID, min_veces: int = 2, limit: int = 20) -> list:
    """Hashes con mayor veces_visto -- el primer detector de fraude recurrente."""
    with get_db_session() as db:
        if db is None:
            return []

        rows = db.execute(
            select(HashDocumento)
            .where(
                HashDocumento.empresa_id == empresa_id,
                HashDocumento.deleted_at.is_(None),
                HashDocumento.veces_visto >= min_veces,
            )
            .order_by(desc(HashDocumento.veces_visto))
            .limit(limit)
        ).scalars().all()

        resultado = []
        for h in rows:
            riesgo_max_row = db.execute(
                select(Analisis.riesgo)
                .where(Analisis.empresa_id == empresa_id, Analisis.hash_sha256 == h.hash_sha256)
                .order_by(desc(Analisis.score_final))
                .limit(1)
            ).scalar_one_or_none()

            resultado.append({
                "hash_sha256": h.hash_sha256,
                "veces_visto": h.veces_visto,
                "primer_analisis": h.primer_analisis.isoformat(),
                "ultimo_analisis": h.ultimo_analisis.isoformat(),
                "riesgo_max": riesgo_max_row,
            })
        return resultado


# ─────────────────────────────────────────────────────────────────
# Nuevas -- item 4.1, Etapa 4. Con el fix de fechas aplicado desde el
# principio (a diferencia de las funciones movidas arriba, que
# heredaban el bug original).
# ─────────────────────────────────────────────────────────────────

def calcular_monto_total_procesado(empresa_id: str = DEFAULT_EMPRESA_ID, fecha_desde: str | None = None, fecha_hasta: str | None = None) -> dict:
    """Suma de monto_detectado en el periodo -- KPI de volumen operado."""
    with get_db_session() as db:
        if db is None:
            return {"monto_total": 0.0, "total_analisis_con_monto": 0}

        filtros = [Analisis.empresa_id == empresa_id, Analisis.deleted_at.is_(None), Analisis.monto_detectado.is_not(None)]
        filtros.extend(_filtro_rango_fechas(fecha_desde, fecha_hasta))

        suma = db.execute(select(func.sum(Analisis.monto_detectado)).where(*filtros)).scalar()
        total = db.execute(select(func.count(Analisis.id)).where(*filtros)).scalar() or 0

        return {
            "monto_total": round(float(suma), 2) if suma is not None else 0.0,
            "total_analisis_con_monto": total,
        }


def calcular_banco_mas_frecuente(empresa_id: str = DEFAULT_EMPRESA_ID, fecha_desde: str | None = None, fecha_hasta: str | None = None, limit: int = 5) -> list:
    """
    Top bancos por VOLUMEN (cuántos análisis) -- distinto de
    calcular_distribucion_scores_por_banco(), que responde "¿qué tan
    riesgoso es cada banco?", no "¿de qué banco recibo más operaciones?".
    """
    with get_db_session() as db:
        if db is None:
            return []

        filtros = [Analisis.empresa_id == empresa_id, Analisis.deleted_at.is_(None), Analisis.banco_detectado.is_not(None)]
        filtros.extend(_filtro_rango_fechas(fecha_desde, fecha_hasta))

        rows = db.execute(
            select(Analisis.banco_detectado, func.count(Analisis.id))
            .where(*filtros)
            .group_by(Analisis.banco_detectado)
            .order_by(desc(func.count(Analisis.id)))
            .limit(limit)
        ).all()
        return [{"banco": banco, "total_analisis": total} for banco, total in rows]


def calcular_riesgo_por_periodo(empresa_id: str = DEFAULT_EMPRESA_ID, fecha_desde: str | None = None, fecha_hasta: str | None = None) -> dict:
    """
    Distribución por riesgo documental (Motor 2) Y por estado_operacion
    (Motor 1) en el periodo -- responde tanto "¿cuánto salió riesgoso?"
    como "¿qué % terminó liquidado/rechazado/etc.?", sin mezclar los dos
    motores en un solo número (ver MOTOR_DECISIONES.md).
    """
    with get_db_session() as db:
        if db is None:
            return {"por_riesgo": [], "por_estado_operacion": []}

        filtros = [Analisis.empresa_id == empresa_id, Analisis.deleted_at.is_(None)]
        filtros.extend(_filtro_rango_fechas(fecha_desde, fecha_hasta))

        por_riesgo_rows = db.execute(
            select(Analisis.riesgo, func.count(Analisis.id)).where(*filtros).group_by(Analisis.riesgo)
        ).all()
        por_estado_rows = db.execute(
            select(Analisis.estado_operacion, func.count(Analisis.id)).where(*filtros).group_by(Analisis.estado_operacion)
        ).all()

        return {
            "por_riesgo": [{"riesgo": r or "INDETERMINADO", "total": c} for r, c in por_riesgo_rows],
            "por_estado_operacion": [{"estado_operacion": e or "no_verificado", "total": c} for e, c in por_estado_rows],
        }


def calcular_alertas_agregadas(empresa_id: str = DEFAULT_EMPRESA_ID) -> dict:
    """
    Conteo de alertas por severidad y por tipo (solo estado NUEVA) --
    responde "¿cuántas alertas críticas activas tengo?" para el
    dashboard. Distinto del conteo puntual de alerta_service.contar_alertas()
    (usado para el badge de BottomNav) -- esta función es la versión
    completa, desagregada por severidad y tipo.
    """
    with get_db_session() as db:
        if db is None:
            return {"por_severidad": [], "por_tipo": [], "activas": 0}

        base = [Alerta.empresa_id == empresa_id, Alerta.deleted_at.is_(None), Alerta.estado == "NUEVA"]

        por_severidad_rows = db.execute(
            select(Alerta.severidad, func.count(Alerta.id)).where(*base).group_by(Alerta.severidad)
        ).all()
        por_tipo_rows = db.execute(
            select(Alerta.tipo_alerta, func.count(Alerta.id)).where(*base).group_by(Alerta.tipo_alerta)
        ).all()
        activas = db.execute(select(func.count(Alerta.id)).where(*base)).scalar() or 0

        return {
            "por_severidad": [{"severidad": s, "total": c} for s, c in por_severidad_rows],
            "por_tipo": [{"tipo_alerta": t, "total": c} for t, c in por_tipo_rows],
            "activas": activas,
        }