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

Item 6.2.7a (Etapa 6): dos dependencias, deliberadamente separadas, no
mezcladas en una sola función con un parámetro "modo transición":

  - obtener_usuario_actual()  -- DEFINITIVA. JWT obligatorio, sin
    fallback de ningún tipo. Sin JWT o JWT inválido -> 401 siempre.

  - obtener_contexto_empresa() -- TRANSICIONAL. Usa el usuario
    autenticado si llega un JWT válido; cae a DEFAULT_EMPRESA_ID
    ÚNICAMENTE si no llega ningún Authorization -- un token presente
    pero inválido nunca cae al default en silencio, se rechaza con 401.

TODO(6.2.8): eliminar obtener_contexto_empresa() por completo cuando el
login del frontend esté funcionando y DEFAULT_EMPRESA_ID se retire del
proyecto. Todo endpoint que hoy use Depends(obtener_contexto_empresa)
debe migrar a Depends(obtener_usuario_actual) en ese momento -- ver
ROADMAP.md item 6.2.8 y DECISION_LOG.md para el registro de esta
decisión temporal con fecha de caducidad explícita.
"""
import os
import uuid
from dataclasses import dataclass
import jwt
from jwt import PyJWKClient
from fastapi import Header, HTTPException
from sqlalchemy import select
from models.usuario import Usuario
from database import get_db_session, DEFAULT_EMPRESA_ID

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
SUPABASE_ISSUER = f"{SUPABASE_URL}/auth/v1"

_jwks_client = PyJWKClient(SUPABASE_JWKS_URL) if SUPABASE_URL else None


def obtener_usuario_actual(authorization: str | None = Header(default=None)) -> Usuario:
    """
    Dependencia DEFINITIVA -- ver ROADMAP.md item 6.2.4c. Sin fallback:
    JWT válido -> usuario. Cualquier otro caso -> 401. Se usa tal cual
    a partir de 6.2.8, cuando DEFAULT_EMPRESA_ID se retire del todo.
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


@dataclass
class ContextoEmpresa:
    """Resultado de obtener_contexto_empresa() -- ver TODO(6.2.8) arriba."""
    empresa_id: str
    usuario: Usuario | None  # None mientras no exista JWT (modo transición)


def obtener_contexto_empresa(authorization: str | None = Header(default=None)) -> ContextoEmpresa:
    """
    Dependencia TRANSICIONAL -- item 6.2.7a. TODO(6.2.8): eliminar esta
    función por completo y migrar todo endpoint que la use a
    Depends(obtener_usuario_actual) antes del lanzamiento público. Ver
    DECISION_LOG.md para el registro de esta decisión con fecha de
    caducidad.

    - Sin Authorization -> DEFAULT_EMPRESA_ID (comportamiento de hoy,
      sin cambios, mientras el frontend no mande JWT todavía).
    - Con Authorization -> debe ser válido. Un token presente pero
      inválido NUNCA cae al default en silencio -- se rechaza con 401,
      igual que obtener_usuario_actual().
    """
    if not authorization:
        return ContextoEmpresa(empresa_id=DEFAULT_EMPRESA_ID, usuario=None)

    usuario = obtener_usuario_actual(authorization=authorization)
    return ContextoEmpresa(empresa_id=str(usuario.empresa_id), usuario=usuario)