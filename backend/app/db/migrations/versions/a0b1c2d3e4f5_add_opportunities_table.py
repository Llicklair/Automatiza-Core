"""Add opportunities table (missing migration)

Revision ID: a0b1c2d3e4f5
Revises: 4ce2419ccd96
Create Date: 2026-03-18 17:00:00.000000

Esta migración crea la tabla 'opportunities' que faltaba en la cadena
de migraciones. Sin ella, cf7da4c31523 (quotes) falla porque intenta
crear una FK a opportunities.id que no existe.

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a0b1c2d3e4f5'
down_revision: str | None = '4ce2419ccd96'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'opportunities',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('expected_value', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('stage', sa.String(length=50), nullable=False, server_default='new'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_opportunities_tenant_id'), 'opportunities', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_opportunities_client_id'), 'opportunities', ['client_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_opportunities_client_id'), table_name='opportunities')
    op.drop_index(op.f('ix_opportunities_tenant_id'), table_name='opportunities')
    op.drop_table('opportunities')
