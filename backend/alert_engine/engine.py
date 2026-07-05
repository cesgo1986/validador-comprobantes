"""
alert_engine/engine.py — Orquestador del Alert Engine (item 3.3, Etapa 3).                                                                                                                                                                                                                                   

Cada regla es una función que recibe el contexto del análisis recién
guardado y devuelve una lista de dicts (o [] si no aplica). Este motor
solo llama a cada regla activa y persiste lo que devuelvan -- agregar
una regla nueva es agregar un archivo y sumarlo a REGLAS_ACTIVAS, no
modificar este archivo.

Ver DECISION_LOG.md, ADR "las alertas son eventos persistentes
generados por un motor de reglas independiente".
"""
from services import alerta_service
from alert_engine.regla_hash import evaluar_hash_reutilizado
from alert_engine.regla_clabe import evaluar_clabe_frecuente
from alert_engine.regla_clave_rastreo import evaluar_clave_rastreo_repetida

REGLAS_ACTIVAS = [
    evaluar_hash_reutilizado,
    evaluar_clabe_frecuente,
    evaluar_clave_rastreo_repetida,
]


def evaluar(contexto: dict) -> list[str]:
    """
    Ejecuta todas las reglas activas contra el contexto del análisis
    recién guardado, y persiste cada alerta que se dispare.

    contexto esperado (ver main.py, llamada a engine.evaluar()):
      {
        "empresa_id": str,
        "analisis_id": str | None,
        "hash_sha256": str | None,
        "veces_visto": int,
        "clabe_detectada": str | None,
        "clave_rastreo": str | None,
        "banco_detectado": str | None,
        "monto_detectado": float | None,
      }

    Devuelve la lista de ids de alertas creadas (puede estar vacía).

    Cualquier excepción de una regla individual se captura sin propagarse
    -- una regla rota no debe tumbar el análisis completo. Mismo
    principio de degradación con gracia que ya usa el resto del sistema
    (CEP, XML): el usuario siempre recibe su resultado principal aunque
    algo secundario falle.
    """
    ids_creados = []
    for regla in REGLAS_ACTIVAS:
        try:
            alertas = regla(contexto) or []
        except Exception as e:
            print(f"Aviso: la regla {regla.__name__} fallo sin detener el analisis:", e)
            continue

        for alerta in alertas:
            try:
                alerta_id = alerta_service.crear_alerta(
                    tipo_alerta=alerta["tipo_alerta"],
                    severidad=alerta["severidad"],
                    entidad_tipo=alerta["entidad_tipo"],
                    entidad_id=alerta["entidad_id"],
                    empresa_id=contexto["empresa_id"],
                    analisis_origen=contexto.get("analisis_id"),
                    metadata=alerta.get("metadata"),
                )
                if alerta_id:
                    ids_creados.append(alerta_id)
            except Exception as e:
                print(f"Aviso: no fue posible persistir una alerta de {regla.__name__}:", e)

    return ids_creados                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              