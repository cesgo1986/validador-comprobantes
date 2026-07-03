"""
services/auditoria_service.py — Persistencia del resultado completo de cada analisis.

Actualizado para multiempresa (empresa_id) y para poblar las columnas
desnormalizadas (archivo_nombre, monto_detectado, banco_detectado, etc.)
que permiten filtros rapidos en el dashboard sin abrir el JSONB.

estado_operacion, fuente_estado y nivel_evidencia se agregaron en
2026-07 (ver DECISION_LOG.md, ADR de desnormalizacion de Estado SPEI) --
mismos valores que main.py ya calcula via scoring_v3.py, sin logica de
extraccion nueva.

Degrada con gracia si DATABASE_URL no esta configurada.
"""
import datetime
import uuid
from models.analisis import Analisis
from database import get_db_session, DEFAULT_EMPRESA_ID


def guardar_analisis(
    hash_sha256: str | None,
    score_claude: float | None,
    score_iat: float | None,
    score_final: float | None,
    riesgo: str | None,
    resultado: dict,
    empresa_id: str = DEFAULT_EMPRESA_ID,
    archivo_nombre: str | None = None,
    archivo_tipo: str | None = None,
    monto_detectado: float | None = None,
    banco_detectado: str | None = None,
    clabe_detectada: str | None = None,
    estado_operacion: str | None = None,
    fuente_estado: str | None = None,
    nivel_evidencia: str | None = None,
) -> str | None:
    """
    Inserta un registro de auditoria. Devuelve el id (UUID como string)
    del registro creado, o None si no hay DB configurada.
    """
    with get_db_session() as db:
        if db is None:
            return None

        registro = Analisis(
            id=uuid.uuid4(),
            empresa_id=empresa_id,
            fecha=datetime.datetime.utcnow(),
            hash_sha256=hash_sha256,
            score_claude=score_claude,
            score_iat=score_iat,
            score_final=score_final,
            riesgo=riesgo,
            estado_operacion=estado_operacion,
            fuente_estado=fuente_estado,
            nivel_evidencia=nivel_evidencia,
            archivo_nombre=archivo_nombre,
            archivo_tipo=archivo_tipo,
            monto_detectado=monto_detectado,
            banco_detectado=banco_detectado,
            clabe_detectada=clabe_detectada,
            resultado=resultado,
        )
        db.add(registro)
        db.flush()
        return str(registro.id)