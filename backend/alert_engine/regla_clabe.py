"""
alert_engine/regla_clabe.py — Regla: CLABE receptora frecuente.

Hipótesis de umbral inicial (2026-07), sujeta a ajuste con datos reales
de la Beta -- ver LABORATORIO.md: 10 o más análisis con la misma CLABE
detectada como destino, dentro de los últimos 30 días, para la misma
empresa.

El umbral es alto a propósito: una cuenta que recibe pagos legítimamente
(una tienda, un negocio activo) puede aparecer decenas de veces sin que
eso sea una señal de fraude -- se busca un salto real de actividad, no
el uso normal de un negocio activo. Este umbral es el candidato más
probable a ajustarse con datos reales de la Beta.
"""
import datetime
from sqlalchemy import select, func
from models.analisis import Analisis
from database import get_db_session

UMBRAL_APARICIONES = 10
VENTANA_DIAS = 30


def evaluar_clabe_frecuente(contexto: dict) -> list[dict]:
    clabe = contexto.get("clabe_detectada")
    empresa_id = contexto.get("empresa_id")
    if not clabe or not empresa_id:
        return []

    with get_db_session() as db:
        if db is None:
            return []

        desde = datetime.datetime.utcnow() - datetime.timedelta(days=VENTANA_DIAS)
        total = db.execute(
            select(func.count(Analisis.id)).where(
                Analisis.empresa_id == empresa_id,
                Analisis.deleted_at.is_(None),
                Analisis.clabe_detectada == clabe,
                Analisis.fecha >= desde,
            )
        ).scalar() or 0

    if total < UMBRAL_APARICIONES:
        return []

    return [{
        "tipo_alerta": "CLABE_FRECUENTE",
        "severidad": "MEDIA",
        "entidad_tipo": "CLABE",
        "entidad_id": clabe,
        "metadata": {"apariciones": total, "ventana_dias": VENTANA_DIAS},
    }]