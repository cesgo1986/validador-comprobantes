"""
models/hash_documento.py — Tabla hashes_documentos, multiempresa.

Cambio clave respecto a la v1: hash_sha256 YA NO es la primary key.
Ahora cada fila tiene su propio id UUID, y la unicidad se garantiza con
UNIQUE(empresa_id, hash_sha256) -- esto permite que el mismo archivo
exista en distintas empresas sin fuga de informacion entre clientes
(la empresa A no puede inferir, ni siquiera indirectamente, que la
empresa B ya subio ese mismo comprobante).

Criterio forense (sin cambios): un hash repetido NO es prueba de fraude
por si solo. Ver services/hash_service.py.
"""
import datetime
import uuid
from sqlalchemy import String, DateTime, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class HashDocumento(Base):
    __tablename__ = "hashes_documentos"
    __table_args__ = (
        UniqueConstraint("empresa_id", "hash_sha256", name="uq_hash_por_empresa"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False)
    hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    primer_analisis: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    ultimo_analisis: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    veces_visto: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )
    deleted_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True)

    empresa = relationship("Empresa", back_populates="hashes_documentos")