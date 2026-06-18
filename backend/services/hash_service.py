"""
services/hash_service.py — Lógica de hash SHA-256 y detección de reutilización.

Diseñado para no tronar la app si DATABASE_URL todavía no está configurada:
si get_db_session() cede None (ver database.py), simplemente se omite el
registro en base de datos y se devuelve el hash con veces_visto=1, sin
lanzar excepción. Esto permite desplegar el cálculo del hash ANTES de
tener PostgreSQL aprovisionado en Render, y activar la persistencia
después sin tocar main.py otra vez.
"""
import hashlib
import datetime
from models.hash_documento import HashDocumento
from database import get_db_session


def calcular_hash(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def registrar_y_consultar_hash(contenido: bytes) -> dict:
    """
    Calcula el SHA-256 del archivo, lo registra (o actualiza el contador
    si ya existía) en hashes_documentos, y devuelve info lista para
    insertar en el resultado del análisis.

    Retorna:
      {
        "hash_documento": str,
        "veces_visto": int,
        "documento_reutilizado": bool,  # True si veces_visto > 1
        "primer_analisis": str | None,  # ISO format, None si es la primera vez
      }
    """
    hash_doc = calcular_hash(contenido)
    ahora = datetime.datetime.utcnow()

    with get_db_session() as db:
        if db is None:
            # DATABASE_URL no configurada todavia: degradamos con gracia,
            # el hash se calcula y se reporta pero no hay persistencia ni
            # deteccion de reutilizacion entre peticiones.
            return {
                "hash_documento": hash_doc,
                "veces_visto": 1,
                "documento_reutilizado": False,
                "primer_analisis": None,
            }

        existente = db.get(HashDocumento, hash_doc)

        if existente:
            existente.veces_visto += 1
            existente.ultimo_analisis = ahora
            primer_analisis_iso = existente.primer_analisis.isoformat()
            veces_visto = existente.veces_visto
        else:
            nuevo = HashDocumento(
                hash_sha256=hash_doc,
                primer_analisis=ahora,
                ultimo_analisis=ahora,
                veces_visto=1,
            )
            db.add(nuevo)
            primer_analisis_iso = ahora.isoformat()
            veces_visto = 1

        return {
            "hash_documento": hash_doc,
            "veces_visto": veces_visto,
            "documento_reutilizado": veces_visto > 1,
            "primer_analisis": primer_analisis_iso,
        }