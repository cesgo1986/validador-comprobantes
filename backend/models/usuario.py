"""
models/usuario.py — Tabla usuarios, relacionada a empresas.

Item 6.2 (Etapa 6, Identity Layer): la autenticacion es Supabase Auth,
no un sistema propio -- ver DECISION_LOG.md, ADR "Supabase Auth como
proveedor de identidad". Esta tabla es el PERFIL de aplicacion (a que
empresa pertenece, que rol tiene) -- la identidad real (contraseña,
correo verificado, sesiones, JWT) vive en Supabase Auth, fuera de este
dominio de negocio.

`supabase_auth_id` enlaza cada fila con el usuario real en Supabase
Auth. Deliberadamente NO se usa el id de Supabase como `id` (PK) de
esta tabla -- nunca dejar que el identificador de un sistema externo
sea la llave primaria de negocio, para que un cambio futuro de
proveedor de autenticacion no rompa el esquema interno.

Roles validos: owner, admin, analyst, viewer.
No se usa un Enum de Postgres a proposito -- un CHECK constraint o
enum requeriria migracion para agregar roles nuevos; un String simple
con validacion en la capa de aplicacion es mas flexible en esta fase.
"""
import datetime
import uuid
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

ROLES_VALIDOS = ("owner", "admin", "analyst", "viewer")

# Item 6.2: valores validos de `status` -- la columna ya existia desde
# la migracion inicial (default "active"), esto solo documenta el set
# completo de valores que la capa de aplicacion debe validar.
ESTADOS_USUARIO_VALIDOS = ("active", "invited", "suspended", "deleted")


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False)

    # Item 6.2: enlace con el usuario real en Supabase Auth. Nullable
    # por ahora (ver la migracion c2f4a91b7d3e) -- se endurece a NOT
    # NULL mas adelante una vez confirmado que todo usuario nuevo la trae.
    supabase_auth_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), unique=True, nullable=True, index=True)

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