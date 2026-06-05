"""Campos de factura rectificativa en `invoices`.

Factura rectificativa / de abono (RD 1619/2012 Art. 15): una nueva factura que
minora una factura anterior con importes negativos. Se persiste el enlace a la
factura original (`rectifies_invoice_id`) y el motivo (`rectification_reason`).
Las facturas anteriores quedan con ambos campos a NULL (no rectifican nada).

Revision ID: 0040_invoice_rectificativa
Revises: 0039_payroll_cuota_solidaridad
"""

import sqlalchemy as sa
from alembic import op

revision = "0040_invoice_rectificativa"
down_revision = "0039_payroll_cuota_solidaridad"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column("rectifies_invoice_id", sa.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column("rectification_reason", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_invoices_rectifies_invoice_id",
        "invoices",
        ["rectifies_invoice_id"],
    )
    op.create_foreign_key(
        "fk_invoices_rectifies_invoice_id",
        "invoices",
        "invoices",
        ["rectifies_invoice_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_invoices_rectifies_invoice_id", "invoices", type_="foreignkey"
    )
    op.drop_index("ix_invoices_rectifies_invoice_id", table_name="invoices")
    op.drop_column("invoices", "rectification_reason")
    op.drop_column("invoices", "rectifies_invoice_id")
