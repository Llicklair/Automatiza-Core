"""Añade invoices.is_simplified (factura simplificada / ticket TPV → TipoFactura F2).

Marca las facturas simplificadas (tickets de TPV sin destinatario identificado,
RD 1619/2012 Art. 4 y 7). En VeriFactu su registro lleva TipoFactura=F2 (lista L2)
en vez de F1. Default false: las facturas existentes son completas.

Revision ID: 0072_invoice_is_simplified
Revises: 0071_invoice_rectifies_once
"""

import sqlalchemy as sa
from alembic import op

revision = "0072_invoice_is_simplified"
down_revision = "0071_invoice_rectifies_once"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column("is_simplified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("invoices", "is_simplified")
