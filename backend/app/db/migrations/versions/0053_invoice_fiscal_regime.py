"""Fiscal: régimen especial + retención IRPF Art.95 en invoices.

Revision ID: 0053_invoice_fiscal_regime
Revises: 0052_sepa_remittances
"""

from alembic import op

revision = "0053_invoice_fiscal_regime"
down_revision = "0052_sepa_remittances"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS fiscal_regime VARCHAR(30)")
    op.execute("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS retencion_irpf_rate NUMERIC(5, 2)")
    op.execute("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS retencion_irpf_amount NUMERIC(10, 2)")


def downgrade() -> None:
    op.execute("ALTER TABLE invoices DROP COLUMN IF EXISTS retencion_irpf_amount")
    op.execute("ALTER TABLE invoices DROP COLUMN IF EXISTS retencion_irpf_rate")
    op.execute("ALTER TABLE invoices DROP COLUMN IF EXISTS fiscal_regime")
