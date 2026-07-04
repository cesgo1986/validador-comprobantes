"""
services/alerta_service.py — Persistencia de alertas (item 3.2, Etapa 3).

Este archivo es solo la capa de persistencia (crear, listar, cambiar
estado) -- las reglas que DETECTAN patrones y deciden cuándo crear una
alerta viven en alert_engine/ (item 3.3, todavía sin implementar). Esta
separación es deliberada: alert_engine/ decide QUÉ alertar, este
servicio decide CÓMO se guarda -- mismo principio de responsabilidad
única que ya se aplicó con cache_service.py y metrics_service.py.

Degrada con gracia si DATABASE_URL no está configurada, igual que el
resto de los servicios.
"""
import datetime
import uuid
from sqlalchemy import select, desc, func
from models.alerta import Alerta
from database import get_db_session, DEFAULT_EMPRESA_ID


def crear_alerta(
    tipo_alerta: str,
    severidad: str,
    entidad_tipo: str,
    entidad_id: str,
    empresa_id: str = DEFAULT_EMPRESA_ID,
    analisis_origen: str | None = None,
    metadata: dict | None = None,
) -> str | None:
    """
    Inserta una alerta. Devuelve el id (UUID como string) del registro
    creado, o None si no hay DB configurada.

    No valida que tipo_alerta/severidad/entidad_tipo pertenezcan a un
    conjunto cerrado de valores -- esa validación vive en alert_engine/
    (cada regla sabe qué tipo/severidad le corresponde). Este servicio
    solo persiste lo que se le pida, para no duplicar esa lógica aquí.
    """
    with get_db_session() as db:
        if db is None:
            return None

        registro = Alerta(
            id=uuid.uuid4(),
            empresa_id=empresa_id,
            tipo_alerta=tipo_alerta,
            severidad=severidad,
            entidad_tipo=entidad_tipo,
            entidad_id=entidad_id,
            analisis_origen=analisis_origen,
            estado="NUEVA",
            metadata_json=metadata,
        )
        db.add(registro)
        db.flush()
        return str(registro.id)


def listar_alertas(
    empresa_id: str = DEFAULT_EMPRESA_ID,
    limit: int = 50,
    offset: int = 0,
    estado: str | None = None,
    severidad: str | None = None,
    tipo_alerta: str | None = None,
) -> dict:
    """Listado paginado de alertas, más reciente primero."""
    with get_db_session() as db:
        if db is None:
            return {"items": [], "total": 0}

        filtros = [Alerta.empresa_id == empresa_id, Alerta.deleted_at.is_(None)]
        if estado:
            filtros.append(Alerta.estado == estado)
        if severidad:
            filtros.append(Alerta.severidad == severidad)
        if tipo_alerta:
            filtros.append(Alerta.tipo_alerta == tipo_alerta)

        total = db.execute(select(func.count(Alerta.id)).where(*filtros)).scalar() or 0

        rows = db.execute(
            select(Alerta)
            .where(*filtros)
            .order_by(desc(Alerta.created_at))
            .limit(limit)
            .offset(offset)
        ).scalars().all()

        items = [
            {
                "id": str(a.id),
                "tipo_alerta": a.tipo_alerta,
                "severidad": a.severidad,
                "entidad_tipo": a.entidad_tipo,
                "entidad_id": a.entidad_id,
                "analisis_origen": str(a.analisis_origen) if a.analisis_origen else None,
                "estado": a.estado,
                "metadata": a.metadata_json,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in rows
        ]
        return {"items": items, "total": total}


def cambiar_estado_alerta(alerta_id: str, nuevo_estado: str, empresa_id: str = DEFAULT_EMPRESA_ID) -> bool:
    """
    Cambia el estado de una alerta (NUEVA -> REVISADA -> DESCARTADA, o
    cualquier transición -- no se restringe el flujo de estados aquí).
    Devuelve True si se actualizó, False si no se encontró o no hay DB.
    """
    with get_db_session() as db:
        if db is None:
            return False

        registro = db.execute(
            select(Alerta).where(
                Alerta.id == alerta_id,
                Alerta.empresa_id == empresa_id,
                Alerta.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if registro is None:
            return False

        registro.estado = nuevo_estado
        registro.updated_at = datetime.datetime.utcnow()
        db.flush()
        return True