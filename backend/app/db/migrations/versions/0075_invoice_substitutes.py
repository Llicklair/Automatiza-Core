"""Añade invoices.substitutes_invoice_id (sustitutiva F3 de facturas simplificadas).

Enlaza una factura completa F3 con la simplificada (ticket) que sustituye; alimenta
el bloque FacturasSustituidas del registro VeriFactu. NULL en facturas ordinarias.

Revision ID: 0075_invoice_substitutes
Revises: 0074_sif_events
"""

from alembic import op

revision = "0075_invoice_substitutes"
down_revision = "0074_sif_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE invoices ADD COLUMN substitutes_invoice_id UUID REFERENCES invoices(id)")
    op.execute("CREATE INDEX ix_invoices_substitutes_invoice_id ON invoices (substitutes_invoice_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_invoices_substitutes_invoice_id")
    op.execute("ALTER TABLE invoices DROP COLUMN substitutes_invoice_id")
