"""LOTES FEFO — Tabla product_lots para trazabilidad por lote y caducidad.

Añade una capa OPCIONAL de lotes sobre el inventario existente. Un producto
puede tener varios lotes, cada uno con su número, fecha de caducidad, cantidad
y coste. La salida de stock descuenta en orden FEFO (First Expired, First Out):
primero el lote que caduca antes.

Es 100% aditivo: no toca `products` ni `stock_movements`. Si un producto no
tiene lotes, el inventario funciona exactamente igual que antes (solo cuenta
`products.stock_quantity`). Ningún consumidor existente necesita cambios.

Revision ID: 0043_product_lots
Revises: 0042_document_source_entity
"""

from alembic import op

revision = "0043_product_lots"
down_revision = "0042_document_source_entity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE IF NOT EXISTS product_lots ("
        "  id UUID PRIMARY KEY, "
        "  tenant_id UUID NOT NULL REFERENCES tenants(id), "
        "  product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE, "
        "  lot_number VARCHAR(100) NOT NULL, "
        "  expiry_date DATE, "
        "  quantity INTEGER NOT NULL DEFAULT 0, "
        "  cost_price NUMERIC(10, 2), "
        "  received_at TIMESTAMPTZ NOT NULL DEFAULT now(), "
        "  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), "
        "  updated_at TIMESTAMPTZ"
        ")"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_product_lots_tenant_id ON product_lots(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_product_lots_product_id ON product_lots(product_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_product_lots_expiry_date ON product_lots(expiry_date)")
    # Orden FEFO eficiente: por producto, lotes con stock ordenados por caducidad.
    op.execute("CREATE INDEX IF NOT EXISTS ix_product_lots_fefo ON product_lots(product_id, expiry_date, received_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_product_lots_fefo")
    op.execute("DROP INDEX IF EXISTS ix_product_lots_expiry_date")
    op.execute("DROP INDEX IF EXISTS ix_product_lots_product_id")
    op.execute("DROP INDEX IF EXISTS ix_product_lots_tenant_id")
    op.execute("DROP TABLE IF EXISTS product_lots")
