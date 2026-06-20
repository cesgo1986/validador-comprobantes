"""
models/usuario.py — Tabla usuarios, relacionada a empresas.

La autenticacion (Supabase Auth, login, etc.) NO esta activa todavia --
esta tabla existe para que el modelo de datos ya tenga la forma correcta
cuando se active, evitando una migracion estructural mas adelante.
Por ahora el dashboard funciona como consola interna sin login.
"""
import datetime
import uuid
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

# Roles validos: owner, admin, analyst, viewer.
# No se usa un Enum de Postgres a proposito -- un CHECK constraint o
# enum requeriria migracion para agregar roles nuevos; un String simple
# con validacion en la capa de aplicacion es mas flexible en esta fase.
ROLES_VALIDOS = ("owner", "admin", "analyst", "viewer")


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=True)
    rol: Mapped[str] = mapped_column(String(20), nullable=False, default="viewer")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )
    deleted_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True)

    empresa = relationship("Empresa", back_populates="usuarios")