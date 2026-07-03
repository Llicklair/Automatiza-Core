"""Anti doble-pago SEPA: índice único parcial en órdenes de remesa.

Cierra la MISMA clase de bug TOCTOU que 0067 (guard check-then-act en la app sin
barrera en BD): dos generaciones de remesa concurrentes con la misma factura/
nómina pasaban `_assert_links_free` a la vez → doble adeudo/transferencia SEPA.

Añade `is_cancelled` a las órdenes (desnormaliza el estado de la remesa padre)
y un índice único PARCIAL por invoice_id/payroll_id que solo cuenta las órdenes
de remesas VIVAS (is_cancelled=false). Cancelar una remesa libera sus elementos.

Antes de crear el índice: backfill (marca canceladas las órdenes de remesas ya
`cancelled`) + dedup defensivo (si hubiera duplicados vivos, conserva el de la
remesa más antigua y marca el resto).

Revision ID: 0070_remittance_order_idempotency
Revises: 0069_hr_documents_tz
"""

import sqlalchemy as sa
from alembic import op

revision = "0070_remittance_order_idempotency"
down_revision = "0069_hr_documents_tz"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sepa_remittance_orders",
        sa.Column("is_cancelled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    # Backfill: órdenes cuya remesa padre ya está cancelada → is_cancelled=true.
    op.execute(
        """
        UPDATE sepa_remittance_orders o
        SET is_cancelled = true
        FROM sepa_remittances r
        WHERE o.remittance_id = r.id AND r.status = 'cancelled'
        """
    )

    # Dedup defensivo (no debería haber duplicados; la feature es nueva): entre
    # órdenes VIVAS con el mismo invoice_id/payroll_id, conserva la de la remesa
    # más antigua y marca el resto is_cancelled=true.
    for col in ("invoice_id", "payroll_id"):
        op.execute(
            f"""
            UPDATE sepa_remittance_orders
            SET is_cancelled = true
            WHERE id IN (
                SELECT o.id FROM (
                    SELECT o.id, row_number() OVER (
                        PARTITION BY o.{col}
                        ORDER BY r.created_at ASC, o.id ASC
                    ) AS rn
                    FROM sepa_remittance_orders o
                    JOIN sepa_remittances r ON r.id = o.remittance_id
                    WHERE o.{col} IS NOT NULL AND o.is_cancelled = false
                ) o WHERE o.rn > 1
            )
            """
        )

    op.create_index(
        "uq_remittance_order_invoice_active",
        "sepa_remittance_orders",
        ["invoice_id"],
        unique=True,
        postgresql_where=sa.text("invoice_id IS NOT NULL AND is_cancelled = false"),
    )
    op.create_index(
        "uq_remittance_order_payroll_active",
        "sepa_remittance_orders",
        ["payroll_id"],
        unique=True,
        postgresql_where=sa.text("payroll_id IS NOT NULL AND is_cancelled = false"),
    )


def downgrade() -> None:
    op.drop_index("uq_remittance_order_payroll_active", table_name="sepa_remittance_orders")
    op.drop_index("uq_remittance_order_invoice_active", table_name="sepa_remittance_orders")
    op.drop_column("sepa_remittance_orders", "is_cancelled")
