"""
alert_engine/regla_hash.py — Regla: reutilización del mismo comprobante (hash).

Hipótesis de umbral inicial (2026-07), sujeta a ajuste con datos reales
de la Beta -- ver LABORATORIO.md:
  - 2ª vez visto (veces_visto == 2): severidad BAJA -- puede ser un
    reenvío legítimo o una segunda consulta del mismo usuario, no
    amerita más que un registro (mismo criterio forense ya aplicado en
    hash_service.py: reutilización no es prueba de fraude por sí sola).
  - 3ª-4ª vez: severidad MEDIA.
  - 5+ veces: severidad ALTA.

No corre una query nueva -- reutiliza `veces_visto`, que main.py ya
calcula vía hash_service.registrar_y_consultar_hash() antes de llamar
al Alert Engine.
"""


def evaluar_hash_reutilizado(contexto: dict) -> list[dict]:
    veces_visto = contexto.get("veces_visto") or 1
    hash_sha256 = contexto.get("hash_sha256")

    if veces_visto < 2 or not hash_sha256:
        return []

    if veces_visto >= 5:
        severidad = "ALTA"
    elif veces_visto >= 3:
        severidad = "MEDIA"
    else:
        severidad = "BAJA"

    return [{
        "tipo_alerta": "REUTILIZACION_HASH",
        "severidad": severidad,
        "entidad_tipo": "HASH",
        "entidad_id": hash_sha256,
        "metadata": {"veces_visto": veces_visto},
    }]