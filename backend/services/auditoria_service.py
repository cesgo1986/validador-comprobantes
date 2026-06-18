"""
services/auditoria_service.py — Persistencia del resultado completo de cada análisis.

Igual que hash_service, degrada con gracia si DATABASE_URL no está
configurada: el análisis se sigue devolviendo al usuario normalmente,
simplemente no queda guardado en la tabla `analisis`.
"""
import datetime
from models.analisis import Analisis
from database import get_db_session


def guardar_analisis(hash_sha256: str | None, score_claude: float | None,
                      score_iat: float | None, score_final: float | None,
                      riesgo: str | None, resultado: dict) -> str | None:
    """
    Inserta un registro de auditoría. Devuelve el id (UUID como string)
    del registro creado, o None si no hay DB configurada.
    """
    with get_db_session() as db:
        if db is None:
            return None

        registro = Analisis(
            fecha=datetime.datetime.utcnow(),
            hash_sha256=hash_sha256,
            score_claude=score_claude,
            score_iat=score_iat,
            score_final=score_final,
            riesgo=riesgo,
            resultado=resultado,
        )
        db.add(registro)
        db.flush()  # para que registro.id quede poblado antes del commit
        return str(registro.id)