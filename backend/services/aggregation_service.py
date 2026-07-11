"""
services/aggregation_service.py — AggregationService (item 4.1, Etapa 4).

Única pieza autorizada a construir queries de agregación sobre el
estado del sistema. Ver DECISION_LOG.md, ADR "ningún dashboard consulta
la base de datos o los motores directamente": el flujo obligatorio es
Dashboard → DashboardService → AggregationService → Motores/DB.

Item 5.5 (Etapa 5, Centro Operativo): 3 agregaciones nuevas al final de
este archivo -- calcular_banco_mayor_incidencia, calcular_comparacion_volumen,
calcular_comparacion_alertas. Ninguna requiere dato nuevo -- todas son
cálculos sobre relaciones/columnas que ya existen (Alerta.analisis_origen,
Alerta.created_at, Analisis.fecha). Ver DECISION_LOG.md, corrección de
factibilidad hecha antes de escribir este código.

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
    la consulta completa por un dato malformado.
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
        condiciones.append(Analisis.fecha < (fh + datetime.timedelta(days=1)))
    return condiciones


# ─────────────────────────────────────────────────────────────────
# Movidas desde dashboard_service.py (item 4.1), con el fix de fechas.
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
# Item 4.1, Etapa 4. Con el fix de fechas aplicado desde el principio.
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
    (Motor 1) en el periodo -- sin mezclar los dos motores en un solo
    número (ver MOTOR_DECISIONES.md).
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
    Conteo de alertas por severidad y por tipo (solo estado NUEVA).
    Distinto del conteo puntual de alerta_service.contar_alertas()
    (usado para el badge de NavigationShell).
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


# ─────────────────────────────────────────────────────────────────
# Item 5.5, Etapa 5 (Centro Operativo). 3 agregaciones nuevas
# identificadas durante la sesión de definición -- ninguna requiere
# dato nuevo, todas usan relaciones/columnas que ya existen. Ver
# DECISION_LOG.md, corrección de factibilidad.
# ─────────────────────────────────────────────────────────────────

def calcular_banco_mayor_incidencia(empresa_id: str = DEFAULT_EMPRESA_ID, fecha_desde: str | None = None, fecha_hasta: str | None = None) -> dict | None:
    """
    Banco cuyos análisis originaron más alertas activas (NUEVA) en el
    periodo -- responde "¿dónde está concentrado mi riesgo?" (Nivel 3
    del Centro Operativo, DESIGN_SYSTEM.md sección 10). Cruza
    Alerta.analisis_origen con Analisis.banco_detectado -- no requiere
    dato nuevo, solo la relación que ya existe. Devuelve None si no hay
    alertas en el periodo -- no se muestra el widget si no hay nada que
    decir (principio de diseño en DECISION_LOG.md).

    Nota (verificado contra models/alerta.py): `analisis_origen` es
    nullable -- una alerta puede originarse de una correlación entre
    varios análisis, no de uno solo. Si ninguna alerta activa tiene ese
    campo lleno, esta función devuelve None con gracia (el JOIN
    simplemente no encuentra nada) -- eso no es un bug de esta query,
    puede ser señal de que las reglas del Alert Engine no están
    llenando `analisis_origen` en la práctica.

    El total del denominador (para el porcentaje) usa exactamente la
    misma población que el desglose por banco (alertas con análisis de
    origen Y banco_detectado no nulos) -- si usaran poblaciones
    distintas, los porcentajes de los distintos bancos no sumarían
    100% entre sí de forma consistente.
    """
    with get_db_session() as db:
        if db is None:
            return None

        filtros_fecha = _filtro_rango_fechas(fecha_desde, fecha_hasta)

        total_alertas = db.execute(
            select(func.count(Alerta.id))
            .select_from(Alerta)
            .join(Analisis, Analisis.id == Alerta.analisis_origen)
            .where(
                Alerta.empresa_id == empresa_id,
                Alerta.deleted_at.is_(None),
                Alerta.estado == "NUEVA",
                Analisis.empresa_id == empresa_id,
                Analisis.deleted_at.is_(None),
                Analisis.banco_detectado.is_not(None),
                *filtros_fecha,
            )
        ).scalar() or 0

        if total_alertas == 0:
            return None

        fila = db.execute(
            select(Analisis.banco_detectado, func.count(Alerta.id))
            .select_from(Alerta)
            .join(Analisis, Analisis.id == Alerta.analisis_origen)
            .where(
                Alerta.empresa_id == empresa_id,
                Alerta.deleted_at.is_(None),
                Alerta.estado == "NUEVA",
                Analisis.empresa_id == empresa_id,
                Analisis.deleted_at.is_(None),
                Analisis.banco_detectado.is_not(None),
                *filtros_fecha,
            )
            .group_by(Analisis.banco_detectado)
            .order_by(desc(func.count(Alerta.id)))
            .limit(1)
        ).first()

        if fila is None:
            return None

        banco, conteo = fila
        return {
            "banco": banco,
            "alertas": conteo,
            "porcentaje_del_total": round((conteo / total_alertas) * 100, 1),
        }


def calcular_comparacion_volumen(empresa_id: str = DEFAULT_EMPRESA_ID, dias_promedio: int = 7) -> dict:
    """
    Compara el volumen de análisis de hoy contra el promedio de los
    `dias_promedio` días anteriores -- responde "¿cómo voy comparado
    con lo normal?" (Nivel 3). `variacion_pct` es None si no hay
    historial suficiente (empresa nueva) -- se omite en vez de mostrar
    una comparación contra cero sin sentido de negocio.
    """
    with get_db_session() as db:
        if db is None:
            return {"hoy": 0, "promedio": None, "variacion_pct": None}

        hoy = datetime.date.today()
        hoy_conteo = db.execute(
            select(func.count(Analisis.id)).where(
                Analisis.empresa_id == empresa_id,
                Analisis.deleted_at.is_(None),
                func.date(Analisis.fecha) == hoy,
            )
        ).scalar() or 0

        desde = hoy - datetime.timedelta(days=dias_promedio)
        rows = db.execute(
            select(func.date(Analisis.fecha), func.count(Analisis.id))
            .where(
                Analisis.empresa_id == empresa_id,
                Analisis.deleted_at.is_(None),
                Analisis.fecha >= desde,
                Analisis.fecha < hoy,
            )
            .group_by(func.date(Analisis.fecha))
        ).all()

        if not rows:
            return {"hoy": hoy_conteo, "promedio": None, "variacion_pct": None}

        promedio = sum(c for _, c in rows) / len(rows)
        variacion = round(((hoy_conteo - promedio) / promedio) * 100, 1) if promedio > 0 else None

        return {
            "hoy": hoy_conteo,
            "promedio": round(promedio, 1),
            "variacion_pct": variacion,
        }


def calcular_comparacion_alertas(empresa_id: str = DEFAULT_EMPRESA_ID) -> dict:
    """
    Compara alertas nuevas de hoy contra ayer -- responde "¿está
    empeorando algo?" (Nivel 3). `variacion_pct` es None si ayer no
    hubo alertas (división entre cero no tiene sentido de negocio).
    """
    with get_db_session() as db:
        if db is None:
            return {"hoy": 0, "ayer": 0, "variacion_pct": None}

        hoy = datetime.date.today()
        ayer = hoy - datetime.timedelta(days=1)

        hoy_conteo = db.execute(
            select(func.count(Alerta.id)).where(
                Alerta.empresa_id == empresa_id,
                Alerta.deleted_at.is_(None),
                func.date(Alerta.created_at) == hoy,
            )
        ).scalar() or 0

        ayer_conteo = db.execute(
            select(func.count(Alerta.id)).where(
                Alerta.empresa_id == empresa_id,
                Alerta.deleted_at.is_(None),
                func.date(Alerta.created_at) == ayer,
            )
        ).scalar() or 0

        variacion = round(((hoy_conteo - ayer_conteo) / ayer_conteo) * 100, 1) if ayer_conteo > 0 else None

        return {
            "hoy": hoy_conteo,
            "ayer": ayer_conteo,
            "variacion_pct": variacion,
        }