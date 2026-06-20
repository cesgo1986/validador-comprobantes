"""
services/hash_service.py — Logica de hash SHA-256 y deteccion de reutilizacion.

Actualizado para multiempresa: ahora se consulta por (empresa_id, hash_sha256)
en vez de usar hash_sha256 como PK directa. Esto aisla los contadores de
veces_visto entre empresas distintas -- la empresa A nunca puede inferir,
ni indirectamente, que la empresa B ya subio el mismo comprobante.

Sigue degradando con gracia si DATABASE_URL no esta configurada.
"""
import hashlib
import datetime
import uuid
from sqlalchemy import select
from models.hash_documento import HashDocumento
from database import get_db_session, DEFAULT_EMPRESA_ID


def calcular_hash(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def registrar_y_consultar_hash(contenido: bytes, empresa_id: str = DEFAULT_EMPRESA_ID) -> dict:
    """
    Calcula el SHA-256 del archivo, lo registra (o actualiza el contador
    si ya existia PARA ESA EMPRESA) en hashes_documentos, y devuelve info
    lista para insertar en el resultado del analisis.

    Retorna:
      {
        "hash_documento": str,
        "veces_visto": int,
        "documento_reutilizado": bool,
        "primer_analisis": str | None,
      }
    """
    hash_doc = calcular_hash(contenido)
    ahora = datetime.datetime.utcnow()

    with get_db_session() as db:
        if db is None:
            return {
                "hash_documento": hash_doc,
                "veces_visto": 1,
                "documento_reutilizado": False,
                "primer_analisis": None,
            }

        stmt = select(HashDocumento).where(
            HashDocumento.empresa_id == empresa_id,
            HashDocumento.hash_sha256 == hash_doc,
        )
        existente = db.execute(stmt).scalar_one_or_none()

        if existente:
            existente.veces_visto += 1
            existente.ultimo_analisis = ahora
            primer_analisis_iso = existente.primer_analisis.isoformat()
            veces_visto = existente.veces_visto
        else:
            nuevo = HashDocumento(
                id=uuid.uuid4(),
                empresa_id=empresa_id,
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