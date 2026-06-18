"""
models/hash_documento.py — Tabla hashes_documentos.

Rastrea el SHA-256 de cada comprobante recibido. Si el mismo archivo
(byte por byte) se sube más de una vez, se incrementa veces_visto.

Importante (criterio forense): un hash repetido NO es prueba de fraude
por sí solo. Detecta "mismo archivo exacto" — no detecta una captura
recortada distinta, un PDF regenerado, o el mismo SPEI exportado de
nuevo con otro formato. Por eso esta señal entra como advertencia
(status warn, +10 al score) y nunca escala el riesgo a ALTO de forma
automática. El fingerprint transaccional (clave_rastreo + fecha + monto
+ destino), que se construye en services/, es la señal fuerte real.
"""
import datetime
from sqlalchemy import String, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class HashDocumento(Base):
    __tablename__ = "hashes_documentos"

    hash_sha256: Mapped[str] = mapped_column(String(64), primary_key=True)
    primer_analisis: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    ultimo_analisis: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    veces_visto: Mapped[int] = mapped_column(Integer, nullable=False, default=1)