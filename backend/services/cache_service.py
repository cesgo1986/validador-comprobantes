"""
services/cache_service.py

Cache generico en memoria del proceso, reutilizable por cualquier
componente del backend (hoy: XML del CEP; a futuro: validacion por QR,
XML manual, historial, etc.). Interfaz deliberadamente simple -- get/set/
delete, con TTL por entrada -- para que el dia que se migre a un backend
distinto (Redis, por ejemplo) solo cambie este archivo, no cada consumidor.

Ver DECISION_LOG.md, ADR "Externalizacion de servicios transversales
(Cache y Metrics)".

Limitacion conocida: vive en memoria del proceso, no es distribuido. Si
Render reinicia la instancia o escala a mas de un worker, el cache no se
comparte entre instancias -- en el peor caso se pierde el ahorro (se
vuelve a consultar la fuente original), nunca se sirve un dato incorrecto.
Migrar a Redis es el siguiente paso natural si el volumen lo justifica, y
al vivir en un servicio propio, ese cambio no toca ningun consumidor.
"""
import time
from typing import Any, Optional

_store: dict[str, dict] = {}


def get(key: str) -> Optional[Any]:
    """Devuelve el valor cacheado si existe y no ha expirado; None en cualquier otro caso."""
    if not key:
        return None
    entry = _store.get(key)
    if not entry:
        return None
    if time.time() - entry["timestamp"] > entry["ttl_segundos"]:
        del _store[key]
        return None
    return entry["valor"]


def set(key: str, valor: Any, ttl_segundos: int = 300) -> None:
    """Guarda un valor con su propio TTL. Cada llamada puede usar un TTL distinto."""
    if not key:
        return
    _store[key] = {"valor": valor, "timestamp": time.time(), "ttl_segundos": ttl_segundos}


def delete(key: str) -> None:
    _store.pop(key, None)


def stats() -> dict:
    """Tamaño actual del cache -- util como señal basica de observabilidad."""
    return {"entradas_activas": len(_store)}