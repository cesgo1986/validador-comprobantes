"""crear tabla alertas

Revision ID: 40c88ed37e49
Revises: b3f2ddaba216
Create Date: 2026-07-04 00:00:00.000000

Item 3.2 (Etapa 3, ROADMAP.md). Ver DECISION_LOG.md, ADR "las alertas
son eventos persistentes generados por un motor de reglas independiente".

tipo_alerta, entidad_tipo, severidad y estado son String, NO un ENUM
nativo de Postgres -- mismo criterio ya usado con estado_operacion
(models/analisis.py): la restriccion de valores permitidos vive en el
codigo (alert_engine/), no en la base de datos, para que agregar un
tipo de alerta nuevo sea agregar un archivo (una regla nueva), no una
migracion.

La columna "metadata" (JSONB) guarda el detalle especifico de cada tipo
de alerta -- cantidad de veces visto, lista de analisis relacionados,
umbral usado, etc. -- sin necesidad de agregar columnas nuevas cuando
aparezcan tipos de alerta futuros (dispositivo, banco, patrones de
comportamiento).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Text
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '40c88ed37e49'
down_revision: Union[str, Sequence[str], None] = 'b3f2ddaba216'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'alertas',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('empresa_id', sa.UUID(), nullable=False),
        sa.Column('tipo_alerta', sa.String(length=50), nullable=False),
        sa.Column('severidad', sa.String(length=20), nullable=False),
        sa.Column('entidad_tipo', sa.String(length=20), nullable=False),
        sa.Column('entidad_id', sa.String(length=255), nullable=False),
        sa.Column('analisis_origen', sa.UUID(), nullable=True),
        sa.Column('estado', sa.String(length=20), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id']),
        sa.ForeignKeyConstraint(['analisis_origen'], ['analisis.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_alertas_empresa_id'), 'alertas', ['empresa_id'], unique=False)
    op.create_index(op.f('ix_alertas_tipo_alerta'), 'alertas', ['tipo_alerta'], unique=False)
    op.create_index(op.f('ix_alertas_severidad'), 'alertas', ['severidad'], unique=False)
    op.create_index(op.f('ix_alertas_entidad_id'), 'alertas', ['entidad_id'], unique=False)
    op.create_index(op.f('ix_alertas_estado'), 'alertas', ['estado'], unique=False)
    op.create_index(op.f('ix_alertas_created_at'), 'alertas', ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_alertas_created_at'), table_name='alertas')
    op.drop_index(op.f('ix_alertas_estado'), table_name='alertas')
    op.drop_index(op.f('ix_alertas_entidad_id'), table_name='alertas')
    op.drop_index(op.f('ix_alertas_severidad'), table_name='alertas')
    op.drop_index(op.f('ix_alertas_tipo_alerta'), table_name='alertas')
    op.drop_index(op.f('ix_alertas_empresa_id'), table_name='alertas')
    op.drop_table('alertas')