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

Confirmado con un JWT real emitido por el proyecto (item 6.2.4b, ver
ROADMAP.md) antes de escribir este archivo -- no se adivinó el
algoritmo ni la forma del token:
  - alg: ES256 (llave asimétrica activa del proyecto)
  - iss: https://<project-ref>.supabase.co/auth/v1
  - aud: "authenticated"
  - sub: UUID del usuario en Supabase Auth (-> usuarios.supabase_auth_id)
"""
import os
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

    Nota sobre el objeto Usuario devuelto: se lee dentro de una sesión
    de base de datos que se cierra al terminar esta función. Es seguro
    usar sus atributos simples (usuario.empresa_id, usuario.rol,
    usuario.id) despues de que la funcion regresa, pero NO acceder a
    relaciones no cargadas (usuario.empresa) sin abrir una sesion nueva
    -- SQLAlchemy no puede hacer lazy-loading de un objeto "detached".
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

    supabase_auth_id = payload.get("sub")
    if not supabase_auth_id:
        raise HTTPException(status_code=401, detail="El token no contiene un identificador de usuario.")

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