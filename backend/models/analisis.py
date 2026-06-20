"""
models/analisis.py — Tabla analisis, multiempresa con columnas desnormalizadas.

resultado (JSONB) sigue guardando el JSON completo del analisis sin
rediseñar el esquema cada vez que main.py agrega un campo nuevo. Las
columnas desnormalizadas (archivo_nombre, monto_detectado, etc.) NO
reemplazan el JSONB -- son una copia plana de los campos mas usados
para filtrar, para no tener que hacer resultado->>'monto' en cada
query. Se rellenan en el mismo punto de main.py donde ya existe
campos_planos, sin logica de extraccion nueva.
"""
import datetime
import uuid
from sqlalchemy import String, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from database import Base


class Analisis(Base):
    __tablename__ = "analisis"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False, index=True)

    fecha: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, default=datetime.datetime.utcnow, index=True)
    hash_sha256: Mapped[str] = mapped_column(String(64), nullable=True, index=True)

    score_claude: Mapped[float] = mapped_column(Numeric, nullable=True)
    score_iat: Mapped[float] = mapped_column(Numeric, nullable=True)
    score_final: Mapped[float] = mapped_column(Numeric, nullable=True)
    riesgo: Mapped[str] = mapped_column(String(32), nullable=True, index=True)

    # Columnas desnormalizadas para filtros rapidos sin abrir el JSONB.
    archivo_nombre: Mapped[str] = mapped_column(String(255), nullable=True)
    archivo_tipo: Mapped[str] = mapped_column(String(50), nullable=True)
    monto_detectado: Mapped[float] = mapped_column(Numeric, nullable=True, index=True)
    banco_detectado: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    clabe_detectada: Mapped[str] = mapped_column(String(18), nullable=True)

    resultado: Mapped[dict] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )
    deleted_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True)

    empresa = relationship("Empresa", back_populates="analisis")