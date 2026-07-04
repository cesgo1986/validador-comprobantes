"""
models/alerta.py — Tabla alertas, generadas por el Alert Engine.

Ver DECISION_LOG.md, ADR "las alertas son eventos persistentes
generados por un motor de reglas independiente". Registra HECHOS
(qué se detectó, sobre qué entidad, desde qué análisis) -- no
interpretaciones ya resueltas. El detalle específico de cada tipo de
alerta vive en la columna `metadata` (JSONB), no en columnas propias,
para que agregar un tipo de alerta nuevo sea agregar una regla (un
archivo en alert_engine/), no una migración.

tipo_alerta, severidad, entidad_tipo y estado son String, no un ENUM
nativo de Postgres -- mismo criterio ya usado con estado_operacion
(models/analisis.py): la restricción de valores permitidos vive en el
código, no en la base de datos.

Nota de nomenclatura: el atributo Python se llama `metadata_json`
(no `metadata`) porque SQLAlchemy reserva `metadata` como atributo
interno de la clase Base -- pero la columna real en la base de datos
sigue llamándose `metadata`, tal como está en el ADR y en la migración.
"""
import datetime
import uuid
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Alerta(Base):
    __tablename__ = "alertas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False, index=True)

    # Qué se detectó -- ver alert_engine/ para los valores en uso hoy
    # (REUTILIZACION_HASH, CLABE_FRECUENTE, CLAVE_RASTREO_REPETIDA, ...).
    tipo_alerta: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severidad: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # BAJA, MEDIA, ALTA, CRITICA

    # Sobre qué entidad -- HASH, CUENTA, CLABE, BANCO, DISPOSITIVO (futuro).
    entidad_tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    entidad_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Desde qué análisis se disparó -- nullable porque una alerta puede
    # originarse de una correlación entre varios análisis, no de uno solo.
    analisis_origen: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("analisis.id"), nullable=True)

    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="NUEVA", index=True)  # NUEVA, REVISADA, DESCARTADA

    # Detalle libre por tipo de alerta -- ej. {"veces_visto": 7, "analisis_relacionados": [...]}
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, default=datetime.datetime.utcnow, index=True)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)

    # Sin back_populates deliberadamente -- no requiere modificar
    # models/empresa.py ni models/analisis.py para funcionar. Si más
    # adelante se necesita navegar empresa.alertas o analisis.alertas,
    # se agrega el back_populates correspondiente en ese momento.
    empresa = relationship("Empresa")
    analisis = relationship("Analisis")