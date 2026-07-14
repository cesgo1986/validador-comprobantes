"""
services/identity_service.py — Identity Engine (item 6.2, Etapa 6).

[Version con diagnostico adicional -- la conversion a uuid.UUID no
resolvio el problema, y el conteo de usuarios sigue en 0 aunque
Supabase SQL Editor muestre la fila. Se agrega diagnostico para
comparar EXACTAMENTE que base de datos/esquema/usuario ve el backend,
contra lo que ve el SQL Editor -- en vez de seguir adivinando.]
"""
import os
import uuid
import logging
import jwt
from jwt import PyJWKClient
from fastapi import Header, HTTPException
from sqlalchemy import select, func, text
from models.usuario import Usuario
from models.empresa import Empresa
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

    with get_db_session() as db:
        if db is None:
            raise HTTPException(status_code=503, detail="Base de datos no disponible.")

        # DEBUG temporal -- diagnostico de conexion real (item 6.2.5).
        diag = db.execute(text("SELECT current_database(), current_schema(), current_user")).first()
        logger.info("DEBUG identity -- current_database=%s current_schema=%s current_user=%s", diag[0], diag[1], diag[2])

        total_empresas = db.execute(select(func.count(Empresa.id))).scalar()
        logger.info("DEBUG identity -- total de filas en empresas (referencia conocida): %s", total_empresas)

        total_usuarios = db.execute(select(func.count(Usuario.id))).scalar()
        logger.info("DEBUG identity -- total de filas en usuarios: %s", total_usuarios)

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