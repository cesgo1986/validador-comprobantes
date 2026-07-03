"""desnormalizar clave_rastreo, referencia y tipo_transferencia en analisis

Revision ID: b3f2ddaba216
Revises: 3b2be7a8c731
Create Date: 2026-07-03 00:00:00.000000

Ver DECISION_LOG.md, ADR "los campos utilizados para busqueda,
correlacion o analitica deben existir como columnas desnormalizadas,
aunque permanezcan integros dentro del JSONB" (2026-07). Item 2.2
(Etapa 2, ROADMAP.md): la busqueda unificada del Historial necesita
clave_rastreo indexada para no depender de JSONB. referencia se agrega
en la misma migracion porque es un identificador igual de fundamental
que probablemente se busque tan seguido como clave_rastreo (Dashboard
Empresa, Etapa 4). tipo_transferencia se siembra sin uso activo todavia
-- hoy siempre sera 'SPEI', pero evita otra migracion cuando VerificaPago
soporte SPID/TEF/transferencias internas.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3f2ddaba216'
down_revision: Union[str, Sequence[str], None] = '3b2be7a8c731'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('analisis', sa.Column('clave_rastreo', sa.String(length=64), nullable=True))
    op.add_column('analisis', sa.Column('referencia', sa.String(length=64), nullable=True))
    op.add_column('analisis', sa.Column('tipo_transferencia', sa.String(length=20), nullable=True))
    op.create_index(op.f('ix_analisis_clave_rastreo'), 'analisis', ['clave_rastreo'], unique=False)
    op.create_index(op.f('ix_analisis_referencia'), 'analisis', ['referencia'], unique=False)
    # tipo_transferencia no lleva indice todavia -- hoy tiene un unico
    # valor posible ('SPEI'), un indice no aporta nada hasta que exista
    # mas de un valor real que filtrar.


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_analisis_referencia'), table_name='analisis')
    op.drop_index(op.f('ix_analisis_clave_rastreo'), table_name='analisis')
    op.drop_column('analisis', 'tipo_transferencia')
    op.drop_column('analisis', 'referencia')
    op.drop_column('analisis', 'clave_rastreo')