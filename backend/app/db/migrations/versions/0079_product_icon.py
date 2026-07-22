"""Vertical tintorería T3: icono/emoji del producto para el catálogo táctil
del modo mostrador. Nullable: sin icono la UI muestra las iniciales.

Revision ID: 0079_product_icon
Revises: 0078_albaran_tintoreria
"""

import sqlalchemy as sa
from alembic import op

revision = "0079_product_icon"
down_revision = "0078_albaran_tintoreria"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("icon", sa.String(8), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "icon")
