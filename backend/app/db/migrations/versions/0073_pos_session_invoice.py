"""Añade pos_sessions.invoice_id (enlace ticket TPV → factura simplificada F2).

Enlaza una sesión de TPV cerrada con la factura simplificada (F2) que emite, y
sirve de guard de idempotencia (una sesión se factura una sola vez). NULL hasta
que se factura.

Revision ID: 0073_pos_session_invoice
Revises: 0072_invoice_is_simplified
"""

from alembic import op

revision = "0073_pos_session_invoice"
down_revision = "0072_invoice_is_simplified"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE pos_sessions ADD COLUMN invoice_id UUID REFERENCES invoices(id)")
    op.execute("CREATE INDEX ix_pos_sessions_invoice_id ON pos_sessions (invoice_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_pos_sessions_invoice_id")
    op.execute("ALTER TABLE pos_sessions DROP COLUMN invoice_id")
