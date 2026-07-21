"""
services/activity_log_service.py — Item 6.3.3 (Etapa 6). Registra
operaciones de negocio en activity_logs. Ver models/activity_log.py
para la filosofía (qué se registra y qué no).

Mismo patrón de degradación con gracia que hash_service.py y
guardar_analisis(): si la base de datos falla al registrar la
actividad, NO debe romper la operación principal que se estaba
auditando -- un análisis exitoso no debe fallar porque el log de
actividad no se pudo escribir. Se registra el error con logger, no se
relanza la excepción.
"""
import logging
import uuid
from models.activity_log import ActivityLog, AuditAction
from database import get_db_session

logger = logging.getLogger("verificapago")


def registrar_actividad(
    empresa_id: str,
    usuario_id: str,
    accion: AuditAction,
    recurso_id: str | None = None,
    metadata: dict | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    try:
        with get_db_session() as db:
            if db is None:
                return
            log = ActivityLog(
                empresa_id=uuid.UUID(empresa_id) if isinstance(empresa_id, str) else empresa_id,
                usuario_id=uuid.UUID(usuario_id) if isinstance(usuario_id, str) else usuario_id,
                accion=accion.value,
                recurso_id=uuid.UUID(recurso_id) if recurso_id else None,
                metadata_json=metadata,
                ip=ip,
                user_agent=user_agent,
            )
            db.add(log)
    except Exception as e:
        logger.warning("No fue posible registrar actividad (%s): %s", accion.value, e)