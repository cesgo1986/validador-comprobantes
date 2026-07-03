"""
services/metrics_service.py

Metricas en memoria del proceso, reutilizables por cualquier componente
del backend. Cada componente registra sus eventos bajo un "servicio"
(namespace de texto libre, ej. "xml", "ocr", "claude", "historial"), y
consulta sus propias metricas con obtener_metricas(servicio).

Ver DECISION_LOG.md, ADR "Externalizacion de servicios transversales
(Cache y Metrics)".

Limitacion conocida: en memoria del proceso, no distribuidas ni
persistentes entre reinicios. Suficiente para observabilidad basica sin
agregar dependencias nuevas todavia -- migrar a Prometheus/Grafana (u
otra herramienta) es el siguiente paso natural si el volumen lo
justifica, y al vivir en un servicio propio, ese cambio no toca ningun
consumidor de las metricas.
"""
from typing import Optional

_MAX_MUESTRAS_DURACION = 200

_metricas: dict[str, dict] = {}


def _obtener_o_crear(servicio: str) -> dict:
    if servicio not in _metricas:
        _metricas[servicio] = {
            "consultas_totales": 0,
            "exitos": 0,
            "fallos": 0,
            "cache_hits": 0,
            "cache_miss": 0,
            "reintentos": 0,
            "timeouts": 0,
            "duraciones_ms": [],
            "eventos": {},  # contador libre por tipo de evento del dominio
        }
    return _metricas[servicio]


def _registrar_duracion(m: dict, duracion_ms: float) -> None:
    m["duraciones_ms"].append(duracion_ms)
    if len(m["duraciones_ms"]) > _MAX_MUESTRAS_DURACION:
        m["duraciones_ms"].pop(0)


def registrar_evento(servicio: str, evento: str) -> None:
    """
    Contador libre para eventos especificos del dominio de cada servicio,
    ej. registrar_evento('xml', 'xml_no_encontrado'). No requiere
    declarar los eventos de antemano -- el primer registro los crea.
    """
    m = _obtener_o_crear(servicio)
    m["eventos"][evento] = m["eventos"].get(evento, 0) + 1


def registrar_exito(servicio: str, duracion_ms: Optional[float] = None) -> None:
    m = _obtener_o_crear(servicio)
    m["consultas_totales"] += 1
    m["exitos"] += 1
    if duracion_ms is not None:
        _registrar_duracion(m, duracion_ms)


def registrar_error(servicio: str, duracion_ms: Optional[float] = None, timeout: bool = False) -> None:
    m = _obtener_o_crear(servicio)
    m["consultas_totales"] += 1
    m["fallos"] += 1
    if timeout:
        m["timeouts"] += 1
    if duracion_ms is not None:
        _registrar_duracion(m, duracion_ms)


def registrar_reintento(servicio: str) -> None:
    _obtener_o_crear(servicio)["reintentos"] += 1


def registrar_cache_hit(servicio: str) -> None:
    _obtener_o_crear(servicio)["cache_hits"] += 1


def registrar_cache_miss(servicio: str) -> None:
    _obtener_o_crear(servicio)["cache_miss"] += 1


def obtener_metricas(servicio: str) -> dict:
    m = _metricas.get(servicio)
    if not m:
        return {
            "servicio": servicio, "consultas_totales": 0, "exitos": 0, "fallos": 0,
            "cache_hits": 0, "cache_miss": 0, "reintentos": 0, "timeouts": 0,
            "duracion_promedio_ms": None, "duracion_minima_ms": None, "duracion_maxima_ms": None,
            "tasa_exito_pct": None, "eventos": {},
            "nota": "Metricas en memoria del proceso, no distribuidas ni persistentes entre reinicios.",
        }
    duraciones = m["duraciones_ms"]
    total_resueltas = m["exitos"] + m["fallos"]
    return {
        "servicio": servicio,
        "consultas_totales": m["consultas_totales"],
        "exitos": m["exitos"],
        "fallos": m["fallos"],
        "cache_hits": m["cache_hits"],
        "cache_miss": m["cache_miss"],
        "reintentos": m["reintentos"],
        "timeouts": m["timeouts"],
        "duracion_promedio_ms": round(sum(duraciones) / len(duraciones), 1) if duraciones else None,
        "duracion_minima_ms": round(min(duraciones), 1) if duraciones else None,
        "duracion_maxima_ms": round(max(duraciones), 1) if duraciones else None,
        "tasa_exito_pct": round(m["exitos"] / total_resueltas * 100, 1) if total_resueltas else None,
        "eventos": dict(m["eventos"]),
        "nota": "Metricas en memoria del proceso, no distribuidas ni persistentes entre reinicios.",
    }