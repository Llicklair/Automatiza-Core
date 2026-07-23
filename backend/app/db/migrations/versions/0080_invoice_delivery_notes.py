"""Vertical tintorería T7: enlace N:M factura ↔ albarán.

`invoice_delivery_notes`: una factura agrupa varios albaranes (cliente empresa
con factura a fin de mes) y un albarán puede colgar de varias facturas. El
único (invoice_id, albaran_id) impide enlaces duplicados; los enlaces vivos
impiden el doble cobro en el flujo "facturar albaranes".

Revision ID: 0080_invoice_delivery_notes
Revises: 0079_product_icon
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0080_invoice_delivery_notes"
down_revision = "0079_product_icon"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invoice_delivery_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column(
            "invoice_id",
            UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "albaran_id",
            UUID(as_uuid=True),
            sa.ForeignKey("delivery_notes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("invoice_id", "albaran_id", name="uq_invoice_albaran"),
    )


def downgrade() -> None:
    op.drop_table("invoice_delivery_notes")
