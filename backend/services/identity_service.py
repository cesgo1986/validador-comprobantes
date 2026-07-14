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

Validado de punta a punta con un usuario real (item 6.2.5, ver
ROADMAP.md): login real -> JWT firmado con ES256 -> validación contra
JWKS -> búsqueda en usuarios -> empresa_id/rol resueltos correctamente.

Dos bugs reales encontrados y corregidos durante esa validación (ver
DECISION_LOG.md para el detalle completo):
  1. El SQL Editor de Supabase no persistía un INSERT manual -- se
     resolvió insertando la fila de prueba vía Table Editor en su lugar.
  2. `database.py` no tenía expire_on_commit=False -- causaba
     DetachedInstanceError al leer atributos de un objeto ORM devuelto
     fuera de get_db_session(). Corregido ahí, no en este archivo.
"""
import os
import uuid
import jwt
from jwt import PyJWKClient
from fastapi import Header, HTTPException
from sqlalchemy import select
from models.usuario import Usuario
from database import get_db_session

# Requiere la variable de entorno SUPABASE_URL configurada en Render
# (ej. https://ujejypvcvuijcyocuzcw.supabase.co) -- mismo patrón que
# ALLOWED_ORIGINS y CLAUDE_MODEL, configuracion por variable de
# entorno, no hardcodeada.
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
SUPABASE_ISSUER = f"{SUPABASE_URL}/auth/v1"

# PyJWKClient descarga y cachea las llaves publicas de Supabase --
# no hace una peticion de red en cada request, solo cuando el cache
# expira o aparece un `kid` que no reconoce (ej. tras una rotacion de
# llaves). Se crea una sola vez, a nivel de modulo.
_jwks_client = PyJWKClient(SUPABASE_JWKS_URL) if SUPABASE_URL else None


def obtener_usuario_actual(authorization: str | None = Header(default=None)) -> Usuario:
    """
    Dependencia de FastAPI (ver ROADMAP.md item 6.2.4c) -- se usa como
    `usuario: Usuario = Depends(obtener_usuario_actual)` en cualquier
    endpoint que requiera autenticación. Reemplaza gradualmente
    DEFAULT_EMPRESA_ID, endpoint por endpoint (item 6.2.7) -- no se
    aplica a todos los endpoints de golpe.
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