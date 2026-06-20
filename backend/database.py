"""
database.py — Configuración de conexión a PostgreSQL con SQLAlchemy 2.x.

Sin cambios respecto a la version anterior: engine sincrono, degradacion
con gracia si DATABASE_URL no esta configurada. Ver models/ para el
schema multiempresa nuevo.
"""
import os
from dotenv import load_dotenv
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)


class Base(DeclarativeBase):
    pass


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
) if DATABASE_URL else None

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False) if engine else None


@contextmanager
def get_db_session():
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
    Crea las tablas si no existen. Para cambios de schema en produccion,
    usar Alembic (alembic upgrade head) en vez de depender de esta funcion.
    """
    if engine is None:
        return False
    from models import empresa, usuario, hash_documento, analisis  # noqa: F401
    Base.metadata.create_all(bind=engine)
    return True


# ID de la empresa "default" usada mientras no exista multiempresa real.
# Fijo (no aleatorio) para que el codigo y las migraciones siempre puedan
# referenciarlo sin tener que consultarlo primero.
DEFAULT_EMPRESA_ID = "00000000-0000-0000-0000-000000000001"