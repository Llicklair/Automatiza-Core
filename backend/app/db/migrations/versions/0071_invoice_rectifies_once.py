"""Anti doble-abono: índice único parcial en invoices.rectifies_invoice_id.

Cierra el mismo TOCTOU que 0067/0070: el guard de aplicación (SELECT-then-insert)
que impide una segunda rectificativa sobre la misma factura original lo saltaban
dos peticiones concurrentes. Una factura original se rectifica UNA sola vez.

Antes del índice: dedup defensivo (conserva la rectificativa más antigua por
original y borra sus líneas + el resto, si hubiera duplicados previos).

Revision ID: 0071_invoice_rectifies_once
Revises: 0070_remittance_order_idempotency
"""

import sqlalchemy as sa
from alembic import op

revision = "0071_invoice_rectifies_once"
down_revision = "0070_remittance_order_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Dedup defensivo: si existieran varias rectificativas para la misma original,
    # conserva la más antigua. Borra primero sus líneas (FK) y luego la factura.
    op.execute(
        """
        DELETE FROM invoice_lines
        WHERE invoice_id IN (
            SELECT id FROM (
                SELECT id, row_number() OVER (
                    PARTITION BY rectifies_invoice_id
                    ORDER BY created_at ASC, id ASC
                ) AS rn
                FROM invoices
                WHERE rectifies_invoice_id IS NOT NULL
            ) t WHERE t.rn > 1
        )
        """
    )
    op.execute(
        """
        DELETE FROM invoices
        WHERE id IN (
            SELECT id FROM (
                SELECT id, row_number() OVER (
                    PARTITION BY rectifies_invoice_id
                    ORDER BY created_at ASC, id ASC
                ) AS rn
                FROM invoices
                WHERE rectifies_invoice_id IS NOT NULL
            ) t WHERE t.rn > 1
        )
        """
    )
    op.create_index(
        "uq_invoices_rectifies_once",
        "invoices",
        ["rectifies_invoice_id"],
        unique=True,
        postgresql_where=sa.text("rectifies_invoice_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_invoices_rectifies_once", table_name="invoices")
