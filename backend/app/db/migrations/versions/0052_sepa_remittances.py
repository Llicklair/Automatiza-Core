"""Tesorería: tablas sepa_remittances y sepa_remittance_orders.

Revision ID: 0052_sepa_remittances
Revises: 0051_employee_pagas
"""

from alembic import op

revision = "0052_sepa_remittances"
down_revision = "0051_employee_pagas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sepa_remittances (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(id),
            remittance_type VARCHAR(20) NOT NULL,
            msg_id VARCHAR(35) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'generated',
            execution_date DATE NOT NULL,
            party_iban VARCHAR(34) NOT NULL,
            nb_of_txs INTEGER NOT NULL,
            total_amount NUMERIC(12, 2) NOT NULL,
            xml TEXT NOT NULL,
            sha256 VARCHAR(64) NOT NULL,
            executed_at TIMESTAMPTZ,
            bank_transaction_id UUID REFERENCES bank_transactions(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_sepa_remittances_tenant_id " "ON sepa_remittances (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sepa_remittances_msg_id " "ON sepa_remittances (msg_id)")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sepa_remittance_orders (
            id UUID PRIMARY KEY,
            remittance_id UUID NOT NULL
                REFERENCES sepa_remittances(id) ON DELETE CASCADE,
            counterparty_name VARCHAR(140) NOT NULL,
            counterparty_iban VARCHAR(34) NOT NULL,
            amount NUMERIC(12, 2) NOT NULL,
            concept VARCHAR(140) DEFAULT '',
            end_to_end_id VARCHAR(35) NOT NULL,
            mandate_id VARCHAR(35),
            mandate_date DATE,
            sequence_type VARCHAR(4),
            invoice_id UUID REFERENCES invoices(id),
            payroll_id UUID REFERENCES payrolls(id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_sepa_remittance_orders_remittance_id "
        "ON sepa_remittance_orders (remittance_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS sepa_remittance_orders")
    op.execute("DROP TABLE IF EXISTS sepa_remittances")
