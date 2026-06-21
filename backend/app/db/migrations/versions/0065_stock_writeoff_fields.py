"""Bajas de stock por rotura/merma: contador de cajas + motivo en movimientos.

Añade:
- `products.stock_boxes`: contador de CAJAS independiente de `stock_quantity`
  (unidades). Sin conversión entre ambos.
- `stock_movements.stock_kind`: "unit" | "box" — sobre qué contador actúa el
  movimiento (y a qué se refiere `stock_after`).
- `stock_movements.reason`: motivo de una baja (rotura/merma/robo/caducado).
  Null en movimientos normales.

`server_default` backfilla las filas existentes (stock_boxes=0, stock_kind='unit').

Revision ID: 0065_stock_writeoff_fields
Revises: 0064_rls_fail_closed
"""

import sqlalchemy as sa
from alembic import op

revision = "0065_stock_writeoff_fields"
down_revision = "0064_rls_fail_closed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("stock_boxes", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "stock_movements",
        sa.Column("stock_kind", sa.String(length=10), nullable=False, server_default="unit"),
    )
    op.add_column(
        "stock_movements",
        sa.Column("reason", sa.String(length=30), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("stock_movements", "reason")
    op.drop_column("stock_movements", "stock_kind")
    op.drop_column("products", "stock_boxes")
