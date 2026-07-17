"""
services/identity_service.py — Identity Engine (item 6.2, Etapa 6).

Ver DECISION_LOG.md, ADR "Supabase Auth como proveedor de identidad".
Este archivo es la primera pieza real del Identity Engine sembrado
junto a Motor SPEI, Motor Documental, Alert Engine y AggregationService
-- responsable de resolver "quién eres" a partir de un JWT, sin emitir
ni firmar tokens propios en ningún caso.

Flujo: JWT recibido -> se valida su firma contra la llave pública de
Supabase (JWKS) -> se extrae `sub` (el ID de usuario de Supabase Auth)
-> se busca ese ID en la tabla `usuarios` (perfil de aplicación) ->
se devuelve el registro con empresa_id/rol ya resueltos.

Item 6.2.8 (Etapa 6, cierre): se retira por completo la dependencia
transicional `obtener_contexto_empresa()` y la clase `ContextoEmpresa`
que existían en este archivo -- ya no queda ni el código ni el
fallback a DEFAULT_EMPRESA_ID. Esto NO significa que DEFAULT_EMPRESA_ID
se elimine del proyecto (sigue siendo el identificador real de la
única empresa que existe hoy en la tabla `empresas`) -- lo que
desaparece es la posibilidad de que una petición SIN JWT sea aceptada
igual. A partir de aquí, toda la aplicación funciona exclusivamente
bajo autenticación real -- ver DECISION_LOG.md.
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


def obtener_usuario_actual(authorization: str | None = Header(default=None)) -> Usuario:
    """
    Dependencia DEFINITIVA y única a partir de 6.2.8 -- ver ROADMAP.md.
    Sin fallback de ningún tipo: JWT válido -> usuario. Cualquier otro
    caso (sin Authorization, token inválido, token expirado, usuario
    sin perfil, usuario suspendido) -> 401 o 403, nunca una respuesta
    con datos.
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