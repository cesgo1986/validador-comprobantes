"""agregar supabase_auth_id a usuarios

Revision ID: c2f4a91b7d3e
Revises: 40c88ed37e49
Create Date: 2026-07-12 00:00:00.000000

Item 6.2 (Etapa 6, Identity Layer). Ver DECISION_LOG.md, ADR "Supabase
Auth como proveedor de identidad" -- usuarios.id NO se usa como el
identificador de Supabase Auth (nunca dejar que el ID de un sistema
externo sea la llave primaria de negocio); se agrega esta columna
separada para enlazar cada fila con su usuario real en Supabase Auth.

Nullable por ahora: la tabla usuarios nunca se ha usado en producción
(autenticacion no estaba activa), pero se agrega como nullable en vez
de NOT NULL por seguridad -- se puede endurecer a NOT NULL en una
migracion posterior una vez confirmado que todo usuario nuevo la trae.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c2f4a91b7d3e'
down_revision: Union[str, Sequence[str], None] = '40c88ed37e49'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('usuarios', sa.Column('supabase_auth_id', sa.UUID(), nullable=True))
    op.create_index(
        op.f('ix_usuarios_supabase_auth_id'),
        'usuarios',
        ['supabase_auth_id'],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_usuarios_supabase_auth_id'), table_name='usuarios')
    op.drop_column('usuarios', 'supabase_auth_id')