"""crear tabla activity_logs

Revision ID: d8f3a2c91e47
Revises: c2f4a91b7d3e
Create Date: 2026-07-14 00:00:00.000000

Item 6.3.4 (Etapa 6, Access Control Layer). Ver DECISION_LOG.md, ADR
"Access Control Layer -- RBAC por permisos, activity_logs (no
audit_logs)". Registra unicamente operaciones de negocio de las que
VerificaPago es dueño -- no duplica eventos de autenticacion que ya
administra Supabase Auth por su cuenta.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd8f3a2c91e47'
down_revision: Union[str, Sequence[str], None] = 'c2f4a91b7d3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'activity_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('empresa_id', sa.UUID(), nullable=False),
        sa.Column('usuario_id', sa.UUID(), nullable=False),
        sa.Column('accion', sa.String(length=50), nullable=False),
        sa.Column('recurso_id', sa.UUID(), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], ),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_activity_logs_empresa_id'), 'activity_logs', ['empresa_id'], unique=False)
    op.create_index(op.f('ix_activity_logs_usuario_id'), 'activity_logs', ['usuario_id'], unique=False)
    op.create_index(op.f('ix_activity_logs_accion'), 'activity_logs', ['accion'], unique=False)
    op.create_index(op.f('ix_activity_logs_created_at'), 'activity_logs', ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_activity_logs_created_at'), table_name='activity_logs')
    op.drop_index(op.f('ix_activity_logs_accion'), table_name='activity_logs')
    op.drop_index(op.f('ix_activity_logs_usuario_id'), table_name='activity_logs')
    op.drop_index(op.f('ix_activity_logs_empresa_id'), table_name='activity_logs')
    op.drop_table('activity_logs')