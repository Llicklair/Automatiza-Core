"""CRM: clients.marketing_consent — opt-in RGPD para email marketing.

Revision ID: 0054_client_mkt_consent
Revises: 0053_invoice_fiscal_regime
"""

from alembic import op

revision = "0054_client_mkt_consent"
down_revision = "0053_invoice_fiscal_regime"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE clients "
        "ADD COLUMN IF NOT EXISTS marketing_consent BOOLEAN NOT NULL DEFAULT FALSE"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE clients DROP COLUMN IF EXISTS marketing_consent")
