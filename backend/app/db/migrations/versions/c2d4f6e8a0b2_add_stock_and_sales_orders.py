"""add stock and sales orders

Revision ID: c2d4f6e8a0b2
Revises: b1e3f8a2c9d0
Create Date: 2026-03-09 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = 'c2d4f6e8a0b2'
down_revision = 'b1e3f8a2c9d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Añadir columnas de stock a products
    op.add_column('products', sa.Column('stock_quantity', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('products', sa.Column('stock_min_alert', sa.Integer(), nullable=False, server_default='0'))

    # 2. Crear tabla de movimientos de stock
    op.create_table(
        'stock_movements',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('movement_type', sa.String(50), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('stock_after', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reference', sa.String(255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_stock_movements_tenant_id', 'stock_movements', ['tenant_id'])
    op.create_index('ix_stock_movements_product_id', 'stock_movements', ['product_id'])

    # 3. Crear tabla de pedidos de venta
    op.create_table(
        'sales_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('order_number', sa.String(100), nullable=True),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('expected_delivery', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('amount_base', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('tax_amount', sa.Numeric(10, 2), nullable=True, server_default='0'),
        sa.Column('amount_total', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('quote_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id']),
        sa.ForeignKeyConstraint(['quote_id'], ['quotes.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_sales_orders_tenant_id', 'sales_orders', ['tenant_id'])
    op.create_index('ix_sales_orders_client_id', 'sales_orders', ['client_id'])
    op.create_index('ix_sales_orders_order_number', 'sales_orders', ['order_number'])

    # 4. Crear tabla de líneas de pedido
    op.create_table(
        'sales_order_lines',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('quantity', sa.Numeric(10, 2), nullable=False, server_default='1'),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('discount_percentage', sa.Numeric(5, 2), nullable=True, server_default='0'),
        sa.Column('tax_percentage', sa.Numeric(5, 2), nullable=True, server_default='21'),
        sa.Column('total', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['order_id'], ['sales_orders.id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_sales_order_lines_order_id', 'sales_order_lines', ['order_id'])


def downgrade() -> None:
    op.drop_table('sales_order_lines')
    op.drop_table('sales_orders')
    op.drop_table('stock_movements')
    op.drop_column('products', 'stock_min_alert')
    op.drop_column('products', 'stock_quantity')
