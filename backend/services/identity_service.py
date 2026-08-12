"""
services/identity_service.py — Identity Engine (item 6.2, Etapa 6).

Ver DECISION_LOG.md, ADR "Supabase Auth como proveedor de identidad".
Item 6.2.6: se extrae _validar_jwt() como función reutilizable -- la
necesita también el flujo de aceptar invitación (services/invitacion_service.py),
que valida un JWT real de Supabase pero NO puede usar
obtener_usuario_actual() completo, porque esa persona todavía no tiene
fila en `usuarios` en el momento exacto de aceptar su invitación (el
vínculo se crea justo en ese paso).
"""
import os
import uuid
import jwt
from jwt import PyJWKClient
from fastapi import Header, HTTPException
from sqlalchemy import select
from models.usuario import Usuario
from database import get_db_session

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
SUPABASE_ISSUER = f"{SUPABASE_URL}/auth/v1"

_jwks_client = PyJWKClient(SUPABASE_JWKS_URL) if SUPABASE_URL else None


def _validar_jwt(authorization: str | None) -> dict:
    """
    Valida la firma de un JWT de Supabase y devuelve su payload
    decodificado. No consulta la tabla usuarios -- solo confirma que
    el token es auténtico y no expiró. Usada por obtener_usuario_actual()
    y por el flujo de aceptar invitación.
    """
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

    return payload


def obtener_usuario_actual(authorization: str | None = Header(default=None)) -> Usuario:
    """
    Dependencia DEFINITIVA -- ver ROADMAP.md item 6.2.4c. Sin fallback:
    JWT válido -> usuario. Cualquier otro caso -> 401 o 403.
    """
    payload = _validar_jwt(authorization)

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
