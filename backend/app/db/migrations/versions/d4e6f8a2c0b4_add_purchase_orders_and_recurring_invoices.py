"""add purchase orders and recurring invoices

Revision ID: d4e6f8a2c0b4
Revises: c2d4f6e8a0b2
Create Date: 2026-03-09 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'd4e6f8a2c0b4'
down_revision = 'c2d4f6e8a0b2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Pedidos de compra
    op.create_table(
        'purchase_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('order_number', sa.String(100), nullable=True),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('expected_delivery', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('amount_base', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('tax_amount', sa.Numeric(10, 2), nullable=True, server_default='0'),
        sa.Column('amount_total', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['supplier_id'], ['clients.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_purchase_orders_tenant_id', 'purchase_orders', ['tenant_id'])
    op.create_index('ix_purchase_orders_supplier_id', 'purchase_orders', ['supplier_id'])
    op.create_index('ix_purchase_orders_order_number', 'purchase_orders', ['order_number'])

    # 2. Líneas de pedido de compra
    op.create_table(
        'purchase_order_lines',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('quantity', sa.Numeric(10, 2), nullable=False, server_default='1'),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('tax_percentage', sa.Numeric(5, 2), nullable=True, server_default='21'),
        sa.Column('total', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['order_id'], ['purchase_orders.id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_purchase_order_lines_order_id', 'purchase_order_lines', ['order_id'])

    # 3. Facturas recurrentes
    op.create_table(
        'recurring_invoices',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('interval_type', sa.String(50), nullable=False, server_default='monthly'),
        sa.Column('next_run_date', sa.Date(), nullable=False),
        sa.Column('last_run_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('lines_json', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('terms', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_recurring_invoices_tenant_id', 'recurring_invoices', ['tenant_id'])
    op.create_index('ix_recurring_invoices_next_run_date', 'recurring_invoices', ['next_run_date'])


def downgrade() -> None:
    op.drop_table('recurring_invoices')
    op.drop_table('purchase_order_lines')
    op.drop_table('purchase_orders')
