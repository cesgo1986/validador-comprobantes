"""desnormalizar estado_operacion, fuente_estado y nivel_evidencia en analisis

Revision ID: 3b2be7a8c731
Revises: ade15461db9e
Create Date: 2026-07-03 00:00:00.000000

Ver DECISION_LOG.md, ADR "se desnormaliza estado_operacion, fuente_estado
y nivel_evidencia en la tabla analisis" (2026-07). Historial (Etapa 2) es
el primer modulo que necesita estado_operacion (Motor 1) fuera de
/resultado, pero no sera el ultimo -- Dashboard Empresa, Alertas
Inteligentes y Analitica tambien lo necesitaran. Se desnormaliza ahora,
mientras es barato, en vez de que cada consumidor futuro tenga que leer
el JSONB `resultado` directamente.

Se agregan los 3 campos juntos (no solo estado_operacion) porque ya
existen conceptualmente en el modelo de decision (jerarquia de
evidencia, ver MOTOR_DECISIONES.md) y habilitan filtros futuros sin otra
migracion -- ej. "mostrar solo operaciones confirmadas por XML oficial".
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3b2be7a8c731'
down_revision: Union[str, Sequence[str], None] = 'ade15461db9e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('analisis', sa.Column('estado_operacion', sa.String(length=32), nullable=True))
    op.add_column('analisis', sa.Column('fuente_estado', sa.String(length=32), nullable=True))
    op.add_column('analisis', sa.Column('nivel_evidencia', sa.String(length=32), nullable=True))
    op.create_index(op.f('ix_analisis_estado_operacion'), 'analisis', ['estado_operacion'], unique=False)
    # fuente_estado y nivel_evidencia no llevan indice propio todavia --
    # se filtran casi siempre junto con estado_operacion, no de forma
    # aislada. Si eso cambia (ej. Dashboard Empresa filtra por
    # nivel_evidencia directamente), agregar indice en una migracion
    # separada cuando exista esa necesidad real, no antes.


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_analisis_estado_operacion'), table_name='analisis')
    op.drop_column('analisis', 'nivel_evidencia')
    op.drop_column('analisis', 'fuente_estado')
    op.drop_column('analisis', 'estado_operacion')