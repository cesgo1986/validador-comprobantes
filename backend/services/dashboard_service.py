"""
services/dashboard_service.py — Queries que alimentan los endpoints /api/v1/dashboard/*.

A partir de item 4.1 (Etapa 4, ver DECISION_LOG.md), este servicio ya
NO construye queries de agregación por su cuenta -- las delega a
AggregationService (aggregation_service.py). Este archivo se queda con
dos responsabilidades genuinamente distintas de "agregar":
  1. Listado/detalle/exportación de análisis individuales
     (listar_analisis, obtener_analisis_detalle, exportar_analisis).
  2. Wrappers delgados hacia AggregationService, para no romper los
     endpoints ya en producción que llaman a estas funciones por nombre.

FIX (2026-07): _construir_filtros_analisis() parsea fecha_desde/
fecha_hasta con _parsear_fecha() (de aggregation_service.py) antes de
comparar contra Analisis.fecha -- bug real encontrado al construir el
ítem 4.2 (ver aggregation_service.py para el detalle completo). Afecta
los filtros de fecha de /analisis y /analisis/exportar (ítems 2.1/2.4).

Todos los queries filtran por empresa_id. En este MVP siempre es
DEFAULT_EMPRESA_ID, pero la firma de cada funcion ya recibe empresa_id
como parametro para no requerir cambios cuando se active multiempresa
real con autenticacion.
"""
import datetime
from sqlalchemy import select, func, desc, or_
from models.analisis import Analisis
from models.hash_documento import HashDocumento
from database import get_db_session, DEFAULT_EMPRESA_ID
from services import aggregation_service
from services import alerta_service
from services.aggregation_service import _parsear_fecha


# ─────────────────────────────────────────────────────────────────
# Wrappers hacia AggregationService -- mismo nombre/firma que antes,
# el SQL real vive en aggregation_service.py.
# ─────────────────────────────────────────────────────────────────

def obtener_stats(empresa_id: str = DEFAULT_EMPRESA_ID, fecha_desde: str | None = None, fecha_hasta: str | None = None) -> dict:
    return aggregation_service.calcular_stats_generales(empresa_id, fecha_desde, fecha_hasta)


def tendencia_diaria(empresa_id: str = DEFAULT_EMPRESA_ID, dias: int = 30) -> list:
    return aggregation_service.calcular_tendencia_diaria(empresa_id, dias)


def distribucion_scores_por_banco(empresa_id: str = DEFAULT_EMPRESA_ID, dias: int = 30, min_analisis: int = 1) -> list:
    return aggregation_service.calcular_distribucion_scores_por_banco(empresa_id, dias, min_analisis)


def top_hashes_reutilizados(empresa_id: str = DEFAULT_EMPRESA_ID, min_veces: int = 2, limit: int = 20) -> list:
    return aggregation_service.calcular_top_hashes_reutilizados(empresa_id, min_veces, limit)


# ─────────────────────────────────────────────────────────────────
# Nuevos wrappers hacia AggregationService -- item 4.1, Etapa 4.
# ─────────────────────────────────────────────────────────────────

def obtener_monto_total_procesado(empresa_id: str = DEFAULT_EMPRESA_ID, fecha_desde: str | None = None, fecha_hasta: str | None = None) -> dict:
    return aggregation_service.calcular_monto_total_procesado(empresa_id, fecha_desde, fecha_hasta)


def obtener_banco_mas_frecuente(empresa_id: str = DEFAULT_EMPRESA_ID, fecha_desde: str | None = None, fecha_hasta: str | None = None, limit: int = 5) -> list:
    return aggregation_service.calcular_banco_mas_frecuente(empresa_id, fecha_desde, fecha_hasta, limit)


def obtener_riesgo_por_periodo(empresa_id: str = DEFAULT_EMPRESA_ID, fecha_desde: str | None = None, fecha_hasta: str | None = None) -> dict:
    return aggregation_service.calcular_riesgo_por_periodo(empresa_id, fecha_desde, fecha_hasta)


def obtener_alertas_agregadas(empresa_id: str = DEFAULT_EMPRESA_ID) -> dict:
    return aggregation_service.calcular_alertas_agregadas(empresa_id)


def obtener_resumen_ejecutivo(empresa_id: str = DEFAULT_EMPRESA_ID) -> dict:
    """
    Item 4.2 (Mobile Executive Summary): bundle de datos para la
    tarjeta resumen dentro de Perfil/Empresa -- una sola llamada en vez
    de que el frontend orqueste 3-4 peticiones para armar una tarjeta
    simple. Compone datos de AggregationService y alerta_service, no
    calcula nada nuevo por su cuenta.
    """
    hoy = datetime.date.today().isoformat()
    stats = aggregation_service.calcular_stats_generales(empresa_id, fecha_desde=hoy, fecha_hasta=hoy)
    riesgo = aggregation_service.calcular_riesgo_por_periodo(empresa_id, fecha_desde=hoy, fecha_hasta=hoy)
    conteo_alertas = alerta_service.contar_alertas(empresa_id)

    riesgo_alto = sum(r["total"] for r in riesgo["por_riesgo"] if r["riesgo"] in ("ALTO", "CRITICO"))
    total_estado = sum(e["total"] for e in riesgo["por_estado_operacion"])
    confirmadas = sum(e["total"] for e in riesgo["por_estado_operacion"] if e["estado_operacion"] in ("liquidada", "acreditada"))
    pct_confirmadas = round((confirmadas / total_estado) * 100, 1) if total_estado > 0 else None

    return {
        "analisis_hoy": stats["analisis_hoy"],
        "alertas_nuevas": conteo_alertas["total_nuevas"],
        "alertas_notificables": conteo_alertas["notificables"],
        "riesgo_alto": riesgo_alto,
        "pct_confirmadas": pct_confirmadas,
    }


def obtener_centro_operativo(empresa_id: str = DEFAULT_EMPRESA_ID) -> dict:
    """
    Item 5.5 (Etapa 5): bundle completo para el Centro Operativo -- una
    sola llamada en vez de que el frontend orqueste 7 peticiones.
    Compone AggregationService, no calcula nada nuevo por su cuenta.
    Estructura calcada del wireframe conceptual (DESIGN_SYSTEM.md,
    sección 10) -- Nivel A (Motor de Verdad) únicamente, sin Nivel 4/
    estratégico (depende de datos de Nivel B que no existen todavía).
    """
    hoy = datetime.date.today().isoformat()

    monto = aggregation_service.calcular_monto_total_procesado(empresa_id, fecha_desde=hoy, fecha_hasta=hoy)
    riesgo = aggregation_service.calcular_riesgo_por_periodo(empresa_id, fecha_desde=hoy, fecha_hasta=hoy)
    alertas_agregadas = aggregation_service.calcular_alertas_agregadas(empresa_id)
    hashes_reutilizados = aggregation_service.calcular_top_hashes_reutilizados(empresa_id, min_veces=2, limit=5)
    # Sin filtro de fecha deliberadamente (fix 2026-07): una alerta
    # crítica sin revisar de hace 2 días sigue siendo riesgo actual --
    # filtrarla porque no es "de hoy" escondería riesgo real acumulado
    # en un día tranquilo sin análisis nuevos. Ver aggregation_service.py.
    banco_incidencia = aggregation_service.calcular_banco_mayor_incidencia(empresa_id)
    comparacion_volumen = aggregation_service.calcular_comparacion_volumen(empresa_id)
    comparacion_alertas = aggregation_service.calcular_comparacion_alertas(empresa_id)

    total_estado = sum(e["total"] for e in riesgo["por_estado_operacion"])
    confirmadas = sum(e["total"] for e in riesgo["por_estado_operacion"] if e["estado_operacion"] in ("liquidada", "acreditada"))
    pct_liquidados = round((confirmadas / total_estado) * 100, 1) if total_estado > 0 else None

    alertas_criticas = sum(s["total"] for s in alertas_agregadas["por_severidad"] if s["severidad"] in ("CRITICA", "ALTA"))

    # Nivel 1 (DESIGN_SYSTEM.md sección 10): 🔴 si hay CRITICA activa,
    # 🟠 si hay ALTA (sin CRITICA), 🟢 si no hay ninguna de las dos.
    severidades_activas = {s["severidad"] for s in alertas_agregadas["por_severidad"] if s["total"] > 0}
    if "CRITICA" in severidades_activas:
        estado_general = "rojo"
    elif "ALTA" in severidades_activas:
        estado_general = "naranja"
    else:
        estado_general = "verde"

    return {
        "estado_operacion_general": estado_general,
        "hero": {
            "monto_procesado_hoy": monto["monto_total"],
        },
        "secundarios": {
            "volumen_hoy": comparacion_volumen["hoy"],
            "pct_liquidados": pct_liquidados,
            "alertas_criticas": alertas_criticas,
        },
        "atencion": {
            "alertas_criticas": alertas_criticas,
            "hashes_reutilizados": len(hashes_reutilizados),
        },
        "tendencias": {
            "banco_mayor_incidencia": banco_incidencia,
            "comparacion_volumen": comparacion_volumen,
            "comparacion_alertas": comparacion_alertas,
        },
    }


# ─────────────────────────────────────────────────────────────────
# Listado / detalle / exportación de análisis individuales -- sin
# cambios de comportamiento, salvo el fix de fechas en
# _construir_filtros_analisis().
# ─────────────────────────────────────────────────────────────────

def _parsear_monto_busqueda(texto: str) -> float | None:
    """
    Si el texto de búsqueda es interpretable como un monto (ej. '1234.56'
    o '1,234.56'), lo devuelve como float. Si no, devuelve None -- no es
    un error, simplemente significa que esta búsqueda no aplica al campo
    monto_detectado.
    """
    try:
        return float(texto.replace(",", "").replace("$", "").strip())
    except (ValueError, AttributeError):
        return None


def _construir_filtros_analisis(
    empresa_id: str,
    riesgo: str | None = None,
    estado_operacion: str | None = None,
    hash_sha256: str | None = None,
    banco: str | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    q: str | None = None,
) -> list:
    """
    Construye la lista de condiciones WHERE compartida entre listar_analisis()
    y exportar_analisis() (item 2.4) -- evita mantener la misma lógica de
    filtros duplicada en dos funciones que deben comportarse idéntico.

    FIX (2026-07): fecha_desde/fecha_hasta se parsean con _parsear_fecha()
    antes de comparar contra Analisis.fecha (TIMESTAMP) -- sin esto,
    SQLAlchemy tipa el parámetro como VARCHAR y Postgres rechaza la
    comparación. fecha_hasta ahora incluye el día completo (antes se
    cortaba a las 00:00:00 de ese día).
    """
    filtros = [Analisis.empresa_id == empresa_id, Analisis.deleted_at.is_(None)]
    if riesgo:
        filtros.append(Analisis.riesgo == riesgo)
    if estado_operacion:
        filtros.append(Analisis.estado_operacion == estado_operacion)
    if hash_sha256:
        filtros.append(Analisis.hash_sha256 == hash_sha256)
    if banco:
        filtros.append(Analisis.banco_detectado.ilike(f"%{banco}%"))

    fd = _parsear_fecha(fecha_desde)
    fh = _parsear_fecha(fecha_hasta)
    if fd:
        filtros.append(Analisis.fecha >= fd)
    if fh:
        filtros.append(Analisis.fecha < (fh + datetime.timedelta(days=1)))

    if q and q.strip():
        texto = q.strip()
        condiciones_q = [
            Analisis.banco_detectado.ilike(f"%{texto}%"),
            Analisis.clave_rastreo.ilike(f"%{texto}%"),
            Analisis.referencia.ilike(f"%{texto}%"),
            Analisis.clabe_detectada.ilike(f"%{texto}%"),
        ]
        monto_interpretado = _parsear_monto_busqueda(texto)
        if monto_interpretado is not None:
            condiciones_q.append(Analisis.monto_detectado == monto_interpretado)
        filtros.append(or_(*condiciones_q))

    return filtros


def listar_analisis(
    empresa_id: str = DEFAULT_EMPRESA_ID,
    limit: int = 50,
    offset: int = 0,
    riesgo: str | None = None,
    estado_operacion: str | None = None,
    hash_sha256: str | None = None,
    banco: str | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    q: str | None = None,
) -> dict:
    """
    Listado paginado de analisis, mas reciente primero.

    Item 2.2: `q` es la búsqueda unificada (banco, clave de rastreo,
    referencia, CLABE, o monto). Ver _construir_filtros_analisis().
    """
    with get_db_session() as db:
        if db is None:
            return {"items": [], "total": 0}

        filtros = _construir_filtros_analisis(
            empresa_id, riesgo, estado_operacion, hash_sha256, banco, fecha_desde, fecha_hasta, q
        )

        total = db.execute(select(func.count(Analisis.id)).where(*filtros)).scalar() or 0

        rows = db.execute(
            select(Analisis, HashDocumento.veces_visto)
            .outerjoin(
                HashDocumento,
                (HashDocumento.hash_sha256 == Analisis.hash_sha256)
                & (HashDocumento.empresa_id == Analisis.empresa_id),
            )
            .where(*filtros)
            .order_by(desc(Analisis.fecha))
            .limit(limit)
            .offset(offset)
        ).all()

        items = [
            {
                "id": str(r.id),
                "fecha": r.fecha.isoformat() if r.fecha else None,
                "hash_sha256": r.hash_sha256,
                "score_claude": float(r.score_claude) if r.score_claude is not None else None,
                "score_iat": float(r.score_iat) if r.score_iat is not None else None,
                "score_final": float(r.score_final) if r.score_final is not None else None,
                "riesgo": r.riesgo,
                "estado_operacion": r.estado_operacion,
                "fuente_estado": r.fuente_estado,
                "nivel_evidencia": r.nivel_evidencia,
                "clave_rastreo": r.clave_rastreo,
                "referencia": r.referencia,
                "tipo_transferencia": r.tipo_transferencia,
                "archivo_nombre": r.archivo_nombre,
                "banco_detectado": r.banco_detectado,
                "monto_detectado": float(r.monto_detectado) if r.monto_detectado is not None else None,
                "veces_visto": veces_visto if veces_visto else 1,
            }
            for r, veces_visto in rows
        ]
        return {"items": items, "total": total}


def exportar_analisis(
    empresa_id: str = DEFAULT_EMPRESA_ID,
    riesgo: str | None = None,
    estado_operacion: str | None = None,
    hash_sha256: str | None = None,
    banco: str | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    q: str | None = None,
    limite_maximo: int = 5000,
) -> list[dict]:
    """
    Item 2.4 (ROADMAP.md, Etapa 2): devuelve TODOS los análisis que
    coinciden con los filtros (no paginado, hasta `limite_maximo`), para
    exportar exactamente lo que el usuario ve filtrado en el Historial --
    no solo la página de 20 que tiene cargada en pantalla.

    limite_maximo existe como salvaguarda de recursos (evitar que una
    exportación sin filtros en una cuenta con cientos de miles de
    análisis tumbe el proceso), no como límite de producto -- 5000 filas
    ya es más de lo que cualquier persona revisa útilmente en un CSV.
    """
    with get_db_session() as db:
        if db is None:
            return []

        filtros = _construir_filtros_analisis(
            empresa_id, riesgo, estado_operacion, hash_sha256, banco, fecha_desde, fecha_hasta, q
        )

        rows = db.execute(
            select(Analisis, HashDocumento.veces_visto)
            .outerjoin(
                HashDocumento,
                (HashDocumento.hash_sha256 == Analisis.hash_sha256)
                & (HashDocumento.empresa_id == Analisis.empresa_id),
            )
            .where(*filtros)
            .order_by(desc(Analisis.fecha))
            .limit(limite_maximo)
        ).all()

        return [
            {
                "fecha": r.fecha.isoformat() if r.fecha else "",
                "banco_detectado": r.banco_detectado or "",
                "monto_detectado": float(r.monto_detectado) if r.monto_detectado is not None else None,
                "estado_operacion": r.estado_operacion or "",
                "riesgo": r.riesgo or "",
                "clave_rastreo": r.clave_rastreo or "",
                "referencia": r.referencia or "",
                "hash_sha256": r.hash_sha256 or "",
                "veces_visto": veces_visto if veces_visto else 1,
            }
            for r, veces_visto in rows
        ]


def obtener_analisis_detalle(analisis_id: str, empresa_id: str = DEFAULT_EMPRESA_ID) -> dict | None:
    """Detalle completo de un analisis, incluyendo el JSONB resultado y el historial del hash."""
    with get_db_session() as db:
        if db is None:
            return None

        registro = db.execute(
            select(Analisis).where(
                Analisis.id == analisis_id,
                Analisis.empresa_id == empresa_id,
                Analisis.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if registro is None:
            return None

        historial_hash = None
        if registro.hash_sha256:
            hash_row = db.execute(
                select(HashDocumento).where(
                    HashDocumento.empresa_id == empresa_id,
                    HashDocumento.hash_sha256 == registro.hash_sha256,
                )
            ).scalar_one_or_none()
            if hash_row:
                historial_hash = {
                    "veces_visto": hash_row.veces_visto,
                    "primer_analisis": hash_row.primer_analisis.isoformat(),
                    "ultimo_analisis": hash_row.ultimo_analisis.isoformat(),
                }

        return {
            "id": str(registro.id),
            "fecha": registro.fecha.isoformat() if registro.fecha else None,
            "hash_sha256": registro.hash_sha256,
            "score_claude": float(registro.score_claude) if registro.score_claude is not None else None,
            "score_iat": float(registro.score_iat) if registro.score_iat is not None else None,
            "score_final": float(registro.score_final) if registro.score_final is not None else None,
            "riesgo": registro.riesgo,
            "estado_operacion": registro.estado_operacion,
            "fuente_estado": registro.fuente_estado,
            "nivel_evidencia": registro.nivel_evidencia,
            "clave_rastreo": registro.clave_rastreo,
            "referencia": registro.referencia,
            "tipo_transferencia": registro.tipo_transferencia,
            "archivo_nombre": registro.archivo_nombre,
            "archivo_tipo": registro.archivo_tipo,
            "monto_detectado": float(registro.monto_detectado) if registro.monto_detectado is not None else None,
            "banco_detectado": registro.banco_detectado,
            "clabe_detectada": registro.clabe_detectada,
            "resultado": registro.resultado,
            "historial_hash": historial_hash,
        }