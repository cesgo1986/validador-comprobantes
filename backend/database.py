"""
database.py — Configuración de conexión a PostgreSQL con SQLAlchemy 2.x.

Usamos un engine SINCRONO (no AsyncSession) a propósito: psycopg3 soporta
async nativamente, pero mezclar sesiones async de SQLAlchemy dentro de
endpoints que ya hacen await a Claude/CEP Banxico complica el código sin
beneficio real en este volumen (consultas a una tabla con PK son del orden
de milisegundos). Si el volumen crece y esto se vuelve cuello de botella,
migrar a AsyncSession + asyncpg es el siguiente paso natural.

Variable de entorno esperada:
  DATABASE_URL=postgresql+psycopg://usuario:password@host:5432/nombre_db

En Render, al crear un PostgreSQL administrado, te da una "Internal
Database URL" que normalmente viene como postgresql://... — hay que
agregarle el dialecto +psycopg para que SQLAlchemy use el driver correcto:
postgresql+psycopg://...
"""
import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Render entrega a veces la URL como "postgresql://..." (sin +psycopg).
# La normalizamos para forzar el driver psycopg3.
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)


class Base(DeclarativeBase):
    pass


# pool_pre_ping evita errores por conexiones muertas (Render puede cerrar
# conexiones inactivas) reconectando automáticamente antes de cada uso.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
) if DATABASE_URL else None

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False) if engine else None


@contextmanager
def get_db_session():
    """
    Context manager para usar dentro de endpoints async sin atarse a
    AsyncSession. Uso:

        with get_db_session() as db:
            db.query(...)

    Si DATABASE_URL no está configurada (ej. desarrollo local sin DB),
    cede None — el código que llama debe manejar ese caso con gracia
    (ver hash_service.py) para que la app no truene si todavía no
    has aprovisionado PostgreSQL.
    """
    if SessionLocal is None:
        yield None
        return
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """
    Crea las tablas si no existen. Util para el primer arranque o en
    desarrollo. En producción, una vez que Alembic esté configurado,
    las migraciones reemplazan a esta función para cambios futuros.
    """
    if engine is None:
        return False
    # Importar los modelos aquí para que Base los conozca antes de create_all
    from models import hash_documento, analisis  # noqa: F401
    Base.metadata.create_all(bind=engine)
    return True