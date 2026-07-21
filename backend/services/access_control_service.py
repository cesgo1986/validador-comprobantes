"""
services/access_control_service.py — Access Control Layer (item 6.3,
Etapa 6). Responde "¿qué puedes hacer?", una vez que Identity Layer
(6.2) ya resolvió "¿quién eres?" -- ver DECISION_LOG.md.

Item 6.3.2: cada endpoint declara qué PERMISO necesita, nunca qué
roles acepta directamente -- la matriz rol -> permisos vive en un solo
lugar (ROLE_PERMISSIONS). Si algún día un cliente pide "que mis
Viewers también puedan exportar", se cambia una línea aquí, no cada
endpoint que use ese permiso.

`require_permission(...)` es un reemplazo directo de
`Depends(obtener_usuario_actual)` -- internamente ya llama a esa
dependencia (FastAPI cachea el resultado dentro de la misma petición,
así que no se valida el JWT dos veces), y además verifica el permiso.
Devuelve el mismo objeto Usuario, así que ningún endpoint necesita
cambiar su lógica interna, solo la línea de la dependencia.
"""
from enum import Enum
from fastapi import Depends, HTTPException
from models.usuario import Usuario
from services.identity_service import obtener_usuario_actual


class Permission(str, Enum):
    VIEW = "view"           # ver dashboard, historial, alertas
    OPERATE = "operate"     # analizar comprobantes, cambiar estado de alertas, reprocesar (futuro)
    EXPORT = "export"       # exportar reportes (CSV, futuro: PDF/Excel)
    USERS = "users"         # invitar/gestionar usuarios (sembrado, depende de 6.2.6)
    CONFIG = "config"       # configuración de la empresa (sembrado, sin endpoints todavía)
    API_KEYS = "api_keys"   # crear/revocar API Keys (sembrado, sin endpoints todavía)


# Matriz única -- ver DECISION_LOG.md para la tabla completa acordada
# con roles como filas y permisos como columnas.
ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "owner": {
        Permission.VIEW, Permission.OPERATE, Permission.EXPORT,
        Permission.USERS, Permission.CONFIG, Permission.API_KEYS,
    },
    "admin": {
        Permission.VIEW, Permission.OPERATE, Permission.EXPORT,
        Permission.USERS, Permission.CONFIG,
    },
    "analyst": {
        Permission.VIEW, Permission.OPERATE, Permission.EXPORT,
    },
    "viewer": {
        Permission.VIEW,
    },
}


def require_permission(permiso: Permission):
    """
    Factory de dependencia -- uso: Depends(require_permission(Permission.EXPORT)).
    """
    def _verificar(usuario: Usuario = Depends(obtener_usuario_actual)) -> Usuario:
        permisos_del_rol = ROLE_PERMISSIONS.get(usuario.rol, set())
        if permiso not in permisos_del_rol:
            raise HTTPException(
                status_code=403,
                detail=f"Tu rol ('{usuario.rol}') no tiene permiso para esta acción.",
            )
        return usuario
    return _verificar