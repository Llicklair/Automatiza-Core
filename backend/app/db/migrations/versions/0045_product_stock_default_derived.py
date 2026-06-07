"""MULTI-ALMACÉN (capa 2) — el stock del almacén por defecto se deriva.

El desglose por almacén calcula el almacén por defecto como
`total global − Σ(otros almacenes)`, así que las filas `product_stock` del
almacén por defecto sembradas en 0044 son redundantes. Se eliminan para que
`product_stock` represente solo el stock de almacenes NO-default.

Revision ID: 0045_product_stock_default_derived
Revises: 0044_warehouses
"""

from alembic import op

revision = "0045_product_stock_default_derived"
down_revision = "0044_warehouses"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM product_stock ps USING warehouses w WHERE ps.warehouse_id = w.id AND w.is_default = TRUE")


def downgrade() -> None:
    # Re-siembra el stock del almacén por defecto = total global del producto.
    op.execute(
        "INSERT INTO product_stock (id, tenant_id, product_id, warehouse_id, quantity, updated_at) "
        "SELECT gen_random_uuid(), p.tenant_id, p.id, w.id, p.stock_quantity, now() "
        "FROM products p JOIN warehouses w ON w.tenant_id = p.tenant_id AND w.is_default = TRUE "
        "WHERE NOT EXISTS ("
        "  SELECT 1 FROM product_stock ps WHERE ps.product_id = p.id AND ps.warehouse_id = w.id"
        ")"
    )
