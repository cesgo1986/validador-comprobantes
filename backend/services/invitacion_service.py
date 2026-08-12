"""
services/invitacion_service.py — Item 6.2.6 (Etapa 6). Flujo completo
de invitación de usuarios: crear la fila en `usuarios` (status
"invited"), pedirle a Supabase que mande el correo (vía su API
administrativa, con la Secret Key -- nunca la del frontend), y
vincular al usuario real con esa fila cuando acepta.

Decisión: un usuario = una empresa (2026-07, ver DECISION_LOG.md). Un
correo no puede invitarse si ya existe en OTRA empresa -- se valida
antes de crear la invitación, sin importar el dominio del correo.
"""
import os
import uuid
import httpx
import logging
from fastapi import HTTPException
from sqlalchemy import select
from models.usuario import Usuario, ROLES_VALIDOS
from database import get_db_session
from services.identity_service import _validar_jwt

logger = logging.getLogger("verificapago")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
# Item 6.2.6: requiere la Secret Key de Supabase (sb_secret_...), NUNCA
# la Publishable Key que usa el frontend. Configurar en Render, jamás
# en el código ni en Vercel -- ver DECISION_LOG.md.
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "")


def crear_invitacion(empresa_id: str, email: str, rol: str) -> dict:
    """
    Crea la fila en `usuarios` (status "invited", sin supabase_auth_id
    todavía) y le pide a Supabase que mande el correo de invitación.
    Lanza HTTPException si el correo ya existe en cualquier empresa
    (un usuario = una empresa) o si el rol no es válido.
    """
    if rol not in ROLES_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Rol inválido. Debe ser uno de: {', '.join(ROLES_VALIDOS)}.")
    if not SUPABASE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Invitaciones no configuradas (falta SUPABASE_SECRET_KEY).")

    with get_db_session() as db:
        if db is None:
            raise HTTPException(status_code=503, detail="Base de datos no disponible.")

        existente = db.execute(
            select(Usuario).where(Usuario.email == email, Usuario.deleted_at.is_(None))
        ).scalar_one_or_none()
        if existente is not None:
            raise HTTPException(
                status_code=409,
                detail="Este correo ya está registrado en VerificaPago (en esta empresa o en otra).",
            )

        nuevo_usuario = Usuario(
            id=uuid.uuid4(),
            empresa_id=uuid.UUID(empresa_id),
            supabase_auth_id=None,
            email=email,
            rol=rol,
            status="invited",
        )
        db.add(nuevo_usuario)

    # Fuera del "with" a propósito: si la fila ya se guardó pero la
    # llamada a Supabase falla, es mejor tener un usuario "invited" sin
    # correo enviado (se puede reintentar) que un correo enviado sin
    # ninguna fila que lo respalde.
    _enviar_invitacion_supabase(email)

    return {"email": email, "rol": rol, "status": "invited"}


def _enviar_invitacion_supabase(email: str) -> None:
    frontend_url = os.getenv("FRONTEND_URL", "https://app.verificapago.mx")
    url = f"{SUPABASE_URL}/auth/v1/invite"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
        "apikey": SUPABASE_SECRET_KEY,
        "Content-Type": "application/json",
    }
    params = {"redirect_to": f"{frontend_url}/aceptar-invitacion"}
    body = {"email": email}

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, headers=headers, params=params, json=body)
        if resp.status_code >= 400:
            logger.error("Error al invitar vía Supabase (%s): %s", resp.status_code, resp.text)
            raise HTTPException(status_code=502, detail="No se pudo enviar el correo de invitación.")
    except httpx.HTTPError as e:
        logger.error("Error de red al invitar vía Supabase: %s", e)
        raise HTTPException(status_code=502, detail="No se pudo enviar el correo de invitación.")


def vincular_invitacion(authorization: str | None) -> dict:
    """
    Se llama justo después de que la persona invitada define su
    contraseña por primera vez (en /aceptar-invitacion, frontend). No
    usa obtener_usuario_actual() porque esa dependencia exige que ya
    exista una fila en `usuarios` con ese supabase_auth_id -- que es
    justo lo que este paso crea.
    """
    payload = _validar_jwt(authorization)
    sub = payload.get("sub")
    email = payload.get("email")
    if not sub or not email:
        raise HTTPException(status_code=401, detail="Token sin identificador de usuario o correo.")

    with get_db_session() as db:
        if db is None:
            raise HTTPException(status_code=503, detail="Base de datos no disponible.")

        usuario = db.execute(
            select(Usuario).where(
                Usuario.email == email,
                Usuario.status == "invited",
                Usuario.supabase_auth_id.is_(None),
                Usuario.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if usuario is None:
            raise HTTPException(
                status_code=404,
                detail="No se encontró una invitación pendiente para este correo.",
            )

        usuario.supabase_auth_id = uuid.UUID(sub)
        usuario.status = "active"

        return {"email": usuario.email, "empresa_id": str(usuario.empresa_id), "rol": usuario.rol}
