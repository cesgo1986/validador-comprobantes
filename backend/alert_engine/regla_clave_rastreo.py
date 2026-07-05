"""
alert_engine/regla_clave_rastreo.py — Regla: clave de rastreo repetida
con banco distinto.

A diferencia de la reutilización de hash (mismo archivo exacto) o la
CLABE frecuente (mismo destino, volumen normal de un negocio activo),
esta regla busca algo más específico: la MISMA clave de rastreo
apareciendo con un banco distinto. Una clave de rastreo identifica una
operación real y específica en SPEI -- si aparece con un banco emisor
o receptor diferente, es una contradicción estructural, no una
coincidencia posible.

Revisión (2026-07): la versión inicial de esta regla también comparaba
`monto_detectado`. Se retiró esa comparación -- un monto distinto con
la misma clave de rastreo es más probable que sea un error de OCR
(Claude Vision leyendo mal un dígito del monto) que evidencia real de
fraude, mientras que un banco distinto con la misma clave es una
contradicción estructural mucho más difícil de explicar por error de
lectura. Comparar solo banco reduce falsos positivos sin perder la
señal que de verdad importa. Ver LABORATORIO.md.

Severidad ALTA fija, sin escalado por cantidad -- cualquier ocurrencia
ya es evidencia fuerte.

Si el análisis actual no tiene banco propio para comparar, la regla no
puede detectar un conflicto real y no alerta -- evita falsos positivos
por falta de dato, no por ausencia real de conflicto.
"""
from sqlalchemy import select
from models.analisis import Analisis
from database import get_db_session


def evaluar_clave_rastreo_repetida(contexto: dict) -> list[dict]:
    clave_rastreo = contexto.get("clave_rastreo")
    empresa_id = contexto.get("empresa_id")
    analisis_id = contexto.get("analisis_id")
    banco = contexto.get("banco_detectado")

    if not clave_rastreo or not empresa_id or not banco:
        return []

    filtros = [
        Analisis.empresa_id == empresa_id,
        Analisis.deleted_at.is_(None),
        Analisis.clave_rastreo == clave_rastreo,
        Analisis.banco_detectado.is_not(None),
        Analisis.banco_detectado != banco,
    ]
    if analisis_id:
        filtros.append(Analisis.id != analisis_id)

    with get_db_session() as db:
        if db is None:
            return []

        filas_conflicto = db.execute(
            select(Analisis.id, Analisis.banco_detectado).where(*filtros).limit(10)
        ).all()

    if not filas_conflicto:
        return []

    return [{
        "tipo_alerta": "CLAVE_RASTREO_REPETIDA",
        "severidad": "ALTA",
        "entidad_tipo": "CLAVE_RASTREO",
        "entidad_id": clave_rastreo,
        "metadata": {
            "analisis_relacionados": [str(f.id) for f in filas_conflicto],
            "banco_actual": banco,
            "bancos_conflicto": list({f.banco_detectado for f in filas_conflicto}),
        },
    }]