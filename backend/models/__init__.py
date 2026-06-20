"""
models/empresa.py — Tabla empresas, raiz del esquema multiempresa.

En este MVP solo existe una empresa (la "default", ver database.py),
pero el modelo ya contempla planes, suspension, limites de uso y
api_key_hash para cuando se abra el motor a terceros o se monetice.
"""
import datetime
import uuid
from sqlalchemy import String, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Empresa(Base):
    __tablename__ = "empresas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    plan: Mapped[str] = mapped_column(String(50), nullable=False, default="free")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    # Hash de la API key (nunca se guarda en texto plano). No se usa todavia
    # -- la autenticacion via API key es una fase futura -- pero la columna
    # queda lista para no requerir otra migracion cuando se active.
    api_key_hash: Mapped[str] = mapped_column(String(128), nullable=True)

    # Limites de uso para monetizacion futura. analisis_consumidos no se
    # incrementa automaticamente todavia; queda en 0 hasta que se decida
    # la logica de reseteo mensual y que pasa al exceder limite_mensual.
    limite_mensual: Mapped[int] = mapped_column(Integer, nullable=True)
    analisis_consumidos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )
    deleted_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True)

    usuarios = relationship("Usuario", back_populates="empresa")
    analisis = relationship("Analisis", back_populates="empresa")
    hashes_documentos = relationship("HashDocumento", back_populates="empresa")