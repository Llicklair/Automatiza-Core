"""MULTI-ALMACÉN (capa 1) — almacenes, stock por almacén y warehouse_id.

Aditivo y retrocompatible:
  - Tabla `warehouses` (almacenes/tiendas) con un "Principal" por defecto por tenant.
  - Tabla `product_stock` (stock por producto y almacén); se siembra con el stock
    actual del producto en el almacén por defecto.
  - Columna `warehouse_id` (opcional) en `product_lots` y `stock_movements`,
    rellenada al almacén por defecto del tenant.

`Product.stock_quantity` se mantiene como total global. La lógica de
mantenimiento por almacén (transferencias, FEFO por almacén) llega en la capa 2.

Revision ID: 0044_warehouses
Revises: 0043_product_lots
"""

from alembic import op

revision = "0044_warehouses"
down_revision = "0043_product_lots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── warehouses ────────────────────────────────────────────────────────────
    op.execute(
        "CREATE TABLE IF NOT EXISTS warehouses ("
        "  id UUID PRIMARY KEY, "
        "  tenant_id UUID NOT NULL REFERENCES tenants(id), "
        "  name VARCHAR(150) NOT NULL, "
        "  code VARCHAR(50), "
        "  address VARCHAR(255), "
        "  is_default BOOLEAN NOT NULL DEFAULT FALSE, "
        "  is_active BOOLEAN NOT NULL DEFAULT TRUE, "
        "  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), "
        "  updated_at TIMESTAMPTZ"
        ")"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_warehouses_tenant_id ON warehouses(tenant_id)")

    # Almacén "Principal" por defecto para cada tenant que aún no tenga ninguno.
    op.execute(
        "INSERT INTO warehouses (id, tenant_id, name, is_default, is_active, created_at, updated_at) "
        "SELECT gen_random_uuid(), t.id, 'Principal', TRUE, TRUE, now(), now() "
        "FROM tenants t "
        "WHERE NOT EXISTS (SELECT 1 FROM warehouses w WHERE w.tenant_id = t.id)"
    )

    # ── product_stock (stock por almacén) ─────────────────────────────────────
    op.execute(
        "CREATE TABLE IF NOT EXISTS product_stock ("
        "  id UUID PRIMARY KEY, "
        "  tenant_id UUID NOT NULL REFERENCES tenants(id), "
        "  product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE, "
        "  warehouse_id UUID NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE, "
        "  quantity INTEGER NOT NULL DEFAULT 0, "
        "  updated_at TIMESTAMPTZ, "
        "  CONSTRAINT uq_product_stock_product_warehouse UNIQUE (product_id, warehouse_id)"
        ")"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_product_stock_tenant_id ON product_stock(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_product_stock_product_id ON product_stock(product_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_product_stock_warehouse_id ON product_stock(warehouse_id)")

    # Sembrar stock por almacén = stock global actual, en el almacén por defecto.
    op.execute(
        "INSERT INTO product_stock (id, tenant_id, product_id, warehouse_id, quantity, updated_at) "
        "SELECT gen_random_uuid(), p.tenant_id, p.id, w.id, p.stock_quantity, now() "
        "FROM products p "
        "JOIN warehouses w ON w.tenant_id = p.tenant_id AND w.is_default = TRUE "
        "WHERE NOT EXISTS ("
        "  SELECT 1 FROM product_stock ps WHERE ps.product_id = p.id AND ps.warehouse_id = w.id"
        ")"
    )

    # ── warehouse_id en lotes y movimientos ───────────────────────────────────
    op.execute(
        "ALTER TABLE product_lots ADD COLUMN IF NOT EXISTS warehouse_id UUID REFERENCES warehouses(id) ON DELETE SET NULL"
    )
    op.execute(
        "ALTER TABLE stock_movements ADD COLUMN IF NOT EXISTS warehouse_id UUID REFERENCES warehouses(id) ON DELETE SET NULL"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_product_lots_warehouse_id ON product_lots(warehouse_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_stock_movements_warehouse_id ON stock_movements(warehouse_id)")

    # Rellenar warehouse_id existente al almacén por defecto del tenant.
    op.execute(
        "UPDATE product_lots l SET warehouse_id = w.id "
        "FROM warehouses w WHERE w.tenant_id = l.tenant_id AND w.is_default = TRUE "
        "AND l.warehouse_id IS NULL"
    )
    op.execute(
        "UPDATE stock_movements m SET warehouse_id = w.id "
        "FROM warehouses w WHERE w.tenant_id = m.tenant_id AND w.is_default = TRUE "
        "AND m.warehouse_id IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_stock_movements_warehouse_id")
    op.execute("DROP INDEX IF EXISTS ix_product_lots_warehouse_id")
    op.execute("ALTER TABLE stock_movements DROP COLUMN IF EXISTS warehouse_id")
    op.execute("ALTER TABLE product_lots DROP COLUMN IF EXISTS warehouse_id")
    op.execute("DROP TABLE IF EXISTS product_stock")
    op.execute("DROP TABLE IF EXISTS warehouses")
