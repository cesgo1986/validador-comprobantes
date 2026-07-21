"""
models/activity_log.py — Registro de actividad de negocio (item 6.3.3,
Etapa 6, Access Control Layer).

Deliberadamente NO se llama "audit_log" -- ver DECISION_LOG.md.
"Auditoría" implica registrar absolutamente todo, incluyendo
autenticación (login, logout, recuperación de contraseña, MFA) -- eso
ya lo hace Supabase Auth por su cuenta, y VerificaPago no debe
duplicarlo. Esta tabla registra únicamente las OPERACIONES DE NEGOCIO
de las que VerificaPago es dueño: análisis, exportaciones, cambios de
estado de alertas, y lo que se sume después (invitaciones, API Keys,
configuración).

`recurso_id` siempre es UUID -- nunca un identificador libre, para
evitar errores de escritura. `metadata_json` (JSONB) permite guardar
contexto adicional especifico de cada tipo de accion sin tener que
agregar columnas nuevas cada vez que se registra un caso nuevo (ej.
{"tipo": "csv", "registros": 842} para una exportacion, o
{"estado_anterior": "NUEVA", "estado_nuevo": "REVISADA"} para un
cambio de alerta).
"""
import datetime
import uuid
from enum import Enum
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class AuditAction(str, Enum):
    """
    Acciones registrables. String Enum (no Postgres enum nativo) --
    mismo criterio que ROLES_VALIDOS en models/usuario.py: agregar una
    accion nueva no debe requerir una migracion.
    """
    ANALYSIS_CREATED = "ANALYSIS_CREATED"
    ANALYSIS_REPROCESSED = "ANALYSIS_REPROCESSED"  # sembrado, sin endpoint todavia
    REPORT_EXPORTED = "REPORT_EXPORTED"
    ALERT_UPDATED = "ALERT_UPDATED"
    PROFILE_UPDATED = "PROFILE_UPDATED"            # sembrado
    USER_INVITED = "USER_INVITED"                  # sembrado, depende de 6.2.6
    API_KEY_CREATED = "API_KEY_CREATED"             # sembrado
    API_KEY_REVOKED = "API_KEY_REVOKED"             # sembrado
    SETTINGS_UPDATED = "SETTINGS_UPDATED"           # sembrado


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False, index=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False, index=True)

    accion: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    recurso_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)  # 45 = longitud máxima de IPv6
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, default=datetime.datetime.utcnow, index=True)