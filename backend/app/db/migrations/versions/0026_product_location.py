"""INV.LOC — Ubicación física del producto en almacén.

Añade `products.location` (string libre indexado) para registrar
pasillo/sección/estantería. Texto libre por ahora; cuando exista
tabla `warehouse_locations` se migrará a FK.

Revision ID: 0026_product_location
Revises: 0025_pos_sessions
"""

from alembic import op


revision = "0026_product_location"
down_revision = "0025_pos_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS location VARCHAR(100)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_products_location ON products(location)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_products_location")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS location")
