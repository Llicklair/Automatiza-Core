"""INV.EXT — Extensión de inventario: barcode, coste, unidad, soft-delete, trazabilidad.

Añade campos al modelo de productos y movimientos que el MVP tenía pendientes:

Products:
  - barcode: código EAN/UPC para el flujo del scanner.
  - category: filtro/agrupación libre (string hasta tener tabla `categories`).
  - unit: unidad de medida (ud, kg, l, m, …) — default 'ud'.
  - cost_price: precio de compra → habilita cálculo de margen y valoración.
  - is_active: soft-delete; protege facturas/albaranes históricos.

Stock_movements:
  - user_id: trazabilidad de quién registró el movimiento (FK opcional).
  - unit_cost: coste por unidad en entradas → base para FIFO / coste medio.

Todos los campos son nullable o con default, así que ningún consumidor
existente (rutas, agentes, servicios, scanner, alerts) necesita cambios
para seguir funcionando.

Revision ID: 0024_inventory_extensions
Revises: 0023_verifactu_config
"""

from alembic import op


revision = "0024_inventory_extensions"
down_revision = "0023_verifactu_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── products ─────────────────────────────────────────────────────────────
    op.execute(
        "ALTER TABLE products "
        "ADD COLUMN IF NOT EXISTS barcode VARCHAR(50), "
        "ADD COLUMN IF NOT EXISTS category VARCHAR(100), "
        "ADD COLUMN IF NOT EXISTS unit VARCHAR(20) NOT NULL DEFAULT 'ud', "
        "ADD COLUMN IF NOT EXISTS cost_price NUMERIC(10, 2), "
        "ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_products_barcode ON products(barcode)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_products_category ON products(category)"
    )

    # ── stock_movements ──────────────────────────────────────────────────────
    op.execute(
        "ALTER TABLE stock_movements "
        "ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id), "
        "ADD COLUMN IF NOT EXISTS unit_cost NUMERIC(10, 2)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_stock_movements_user_id "
        "ON stock_movements(user_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_stock_movements_user_id")
    op.execute(
        "ALTER TABLE stock_movements "
        "DROP COLUMN IF EXISTS unit_cost, "
        "DROP COLUMN IF EXISTS user_id"
    )

    op.execute("DROP INDEX IF EXISTS ix_products_category")
    op.execute("DROP INDEX IF EXISTS ix_products_barcode")
    op.execute(
        "ALTER TABLE products "
        "DROP COLUMN IF EXISTS is_active, "
        "DROP COLUMN IF EXISTS cost_price, "
        "DROP COLUMN IF EXISTS unit, "
        "DROP COLUMN IF EXISTS category, "
        "DROP COLUMN IF EXISTS barcode"
    )
