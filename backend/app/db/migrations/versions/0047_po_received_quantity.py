"""RECEPCIÓN — cantidad recibida por línea de pedido de compra.

Permite recepciones parciales: cada línea registra cuánto se ha recibido ya.
El pedido pasa a 'partially_received' o 'received' según corresponda.

Revision ID: 0047_po_received_quantity
Revises: 0046_product_reorder
"""

from alembic import op

revision = "0047_po_received_quantity"
down_revision = "0046_product_reorder"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE purchase_order_lines "
        "ADD COLUMN IF NOT EXISTS received_quantity NUMERIC(10, 2) NOT NULL DEFAULT 0"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE purchase_order_lines DROP COLUMN IF EXISTS received_quantity")
