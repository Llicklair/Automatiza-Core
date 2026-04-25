"""Add cross-domain accounting foreign keys.

Revision ID: 0002_accounting_fks
Revises: 0001_initial_squash
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0002_accounting_fks"
down_revision = "0001_initial_squash"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "journal_entries",
        sa.Column("invoice_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_journal_entries_invoice_id",
        "journal_entries",
        "invoices",
        ["invoice_id"],
        ["id"],
    )
    op.create_index("ix_journal_entries_invoice_id", "journal_entries", ["invoice_id"])

    op.add_column(
        "journal_entries",
        sa.Column("payroll_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_journal_entries_payroll_id",
        "journal_entries",
        "payrolls",
        ["payroll_id"],
        ["id"],
    )
    op.create_index("ix_journal_entries_payroll_id", "journal_entries", ["payroll_id"])

    op.add_column(
        "invoices",
        sa.Column("document_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_invoices_document_id",
        "invoices",
        "tenant_documents",
        ["document_id"],
        ["id"],
    )

    op.add_column(
        "bank_transactions",
        sa.Column("journal_entry_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_bank_transactions_journal_entry_id",
        "bank_transactions",
        "journal_entries",
        ["journal_entry_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_bank_transactions_journal_entry_id", "bank_transactions", type_="foreignkey"
    )
    op.drop_column("bank_transactions", "journal_entry_id")

    op.drop_constraint("fk_invoices_document_id", "invoices", type_="foreignkey")
    op.drop_column("invoices", "document_id")

    op.drop_index("ix_journal_entries_payroll_id", table_name="journal_entries")
    op.drop_constraint("fk_journal_entries_payroll_id", "journal_entries", type_="foreignkey")
    op.drop_column("journal_entries", "payroll_id")

    op.drop_index("ix_journal_entries_invoice_id", table_name="journal_entries")
    op.drop_constraint("fk_journal_entries_invoice_id", "journal_entries", type_="foreignkey")
    op.drop_column("journal_entries", "invoice_id")
