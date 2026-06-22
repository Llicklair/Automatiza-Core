"""Flag is_demo en invoices/clients/products: datos de ejemplo del onboarding.

Los datos demo se siembran desde el wizard de primeros pasos para que el
producto "se vea vivo" en el trial: aparecen en listados y analítica, pero
quedan FUERA de toda declaración fiscal (303/130/390/347/libro registro y de
la cadena VeriFactu) y son borrables de golpe. Ver
backend/app/services/onboarding/seed.py.

`server_default false` backfilla como NO-demo todas las filas reales existentes.

Revision ID: 0066_demo_data_flag
Revises: 0065_stock_writeoff_fields
"""

import sqlalchemy as sa
from alembic import op

revision = "0066_demo_data_flag"
down_revision = "0065_stock_writeoff_fields"
branch_labels = None
depends_on = None

_TABLES = ("invoices", "clients", "products")


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(
            table,
            sa.Column(
                "is_demo",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )


def downgrade() -> None:
    for table in _TABLES:
        op.drop_column(table, "is_demo")
