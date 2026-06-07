"""REPOSICIÓN — proveedor habitual y cantidad de reposición por producto.

Añade a `products`:
  - supplier_id: proveedor habitual (FK clients) para generar pedidos de compra.
  - reorder_quantity: cantidad sugerida a pedir cuando se alcanza el punto de
    pedido (si es NULL, se sugiere llevar el stock al doble del mínimo).

El punto de pedido reutiliza `stock_min_alert`.

Revision ID: 0046_product_reorder
Revises: 0045_product_stock_default_derived
"""

from alembic import op

revision = "0046_product_reorder"
down_revision = "0045_product_stock_default_derived"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS supplier_id UUID REFERENCES clients(id)")
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS reorder_quantity INTEGER")
    op.execute("CREATE INDEX IF NOT EXISTS ix_products_supplier_id ON products(supplier_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_products_supplier_id")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS reorder_quantity")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS supplier_id")
