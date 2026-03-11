"""add_fixed_assets_table

Revision ID: b1e3f8a2c9d0
Revises: a3f7c9e2d1b4
Create Date: 2026-03-09 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b1e3f8a2c9d0'
down_revision: str | None = 'a3f7c9e2d1b4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'fixed_assets',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('purchase_date', sa.Date(), nullable=False),
        sa.Column('purchase_value', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('useful_life_years', sa.Numeric(precision=5, scale=2), nullable=False, server_default='5'),
        sa.Column('residual_value', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0'),
        sa.Column('depreciation_method', sa.String(length=50), nullable=False, server_default='linear'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('account_code', sa.String(length=50), nullable=True),
        sa.Column('reference_invoice', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_fixed_assets_tenant_id'), 'fixed_assets', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_fixed_assets_tenant_id'), table_name='fixed_assets')
    op.drop_table('fixed_assets')
