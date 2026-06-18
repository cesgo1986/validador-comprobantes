"""
models/analisis.py — Tabla analisis (auditoría).

Guarda un registro por cada llamada a /analizar. La columna `resultado`
es JSONB y almacena el JSON completo que ya devuelve el endpoint, así
no hay que rediseñar el esquema cada vez que el backend agrega un campo
nuevo al resultado (cep_resultado, iat_metricas, etc.) — eso vive en el
JSONB tal cual, y las columnas sueltas (score_final, riesgo, hash) son
solo para poder filtrar/indexar rápido sin tener que parsear el JSON.
"""
import datetime
import uuid
from sqlalchemy import String, DateTime, Numeric, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class Analisis(Base):
    __tablename__ = "analisis"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fecha: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    hash_sha256: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    score_claude: Mapped[float] = mapped_column(Numeric, nullable=True)
    score_iat: Mapped[float] = mapped_column(Numeric, nullable=True)
    score_final: Mapped[float] = mapped_column(Numeric, nullable=True)
    riesgo: Mapped[str] = mapped_column(String(32), nullable=True)
    # JSONB es específico de Postgres (más eficiente que JSON genérico para
    # consultas futuras tipo "dame todos los análisis con riesgo=ALTO").
    resultado: Mapped[dict] = mapped_column(JSONB, nullable=True)