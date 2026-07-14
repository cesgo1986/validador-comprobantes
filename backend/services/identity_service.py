"""
services/identity_service.py — Identity Engine (item 6.2, Etapa 6).

[docstring sin cambios respecto a la version anterior -- ver esa
version para el detalle completo. Este archivo agrega LOGS TEMPORALES
de diagnostico (item 6.2.5) porque la conversion a uuid.UUID no
resolvio el problema esperado -- antes de adivinar una segunda causa,
se necesita ver exactamente que esta pasando dentro de la consulta.]
"""
import os
import uuid
import logging
import jwt
from jwt import PyJWKClient
from fastapi import Header, HTTPException
from sqlalchemy import select, func
from models.usuario import Usuario
from database import get_db_session

logger = logging.getLogger("verificapago")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
SUPABASE_ISSUER = f"{SUPABASE_URL}/auth/v1"

_jwks_client = PyJWKClient(SUPABASE_JWKS_URL) if SUPABASE_URL else None


def obtener_usuario_actual(authorization: str | None = Header(default=None)) -> Usuario:
    if _jwks_client is None:
        raise HTTPException(status_code=503, detail="Autenticación no configurada (falta SUPABASE_URL).")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Falta el encabezado Authorization: Bearer <token>.")

    token = authorization.removeprefix("Bearer ").strip()

    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
            issuer=SUPABASE_ISSUER,
        )
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Token inválido o expirado: {e}")

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="El token no contiene un identificador de usuario.")

    try:
        supabase_auth_id = uuid.UUID(sub)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=401, detail="El token contiene un identificador de usuario inválido.")

    # DEBUG temporal (item 6.2.5) -- se quita en cuanto se resuelva.
    logger.info("DEBUG identity -- sub del JWT: %r (tipo %s)", sub, type(sub))
    logger.info("DEBUG identity -- supabase_auth_id convertido: %r (tipo %s)", supabase_auth_id, type(supabase_auth_id))

    with get_db_session() as db:
        if db is None:
            logger.error("DEBUG identity -- get_db_session() devolvió None (sin conexión a la base de datos)")
            raise HTTPException(status_code=503, detail="Base de datos no disponible.")

        # DEBUG temporal: cuántas filas totales hay en usuarios, y
        # cuáles son sus valores de supabase_auth_id -- para ver si el
        # backend está leyendo la misma base de datos donde se insertó
        # la fila manualmente.
        total_usuarios = db.execute(select(func.count(Usuario.id))).scalar()
        logger.info("DEBUG identity -- total de filas en usuarios (sin filtrar): %s", total_usuarios)

        todos = db.execute(select(Usuario.id, Usuario.supabase_auth_id, Usuario.email, Usuario.deleted_at)).all()
        for fila in todos:
            logger.info("DEBUG identity -- fila existente: id=%s supabase_auth_id=%r email=%s deleted_at=%s",
                        fila.id, fila.supabase_auth_id, fila.email, fila.deleted_at)

        usuario = db.execute(
            select(Usuario).where(
                Usuario.supabase_auth_id == supabase_auth_id,
                Usuario.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if usuario is None:
            raise HTTPException(
                status_code=403,
                detail="El usuario está autenticado en Supabase, pero no tiene un perfil en VerificaPago.",
            )
        if usuario.status != "active":
            raise HTTPException(status_code=403, detail=f"Usuario en estado '{usuario.status}', no puede operar.")

        return usuario