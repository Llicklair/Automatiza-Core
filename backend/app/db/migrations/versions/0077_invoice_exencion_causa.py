"""invoices.exencion_causa — causa de exención/no sujeción VeriFactu (E1–E6,
N1, N2) para facturas con IVA al 0%. Alimenta la calificación real del
DetalleDesglose (antes S1 fija, incorrecta para exentas/no sujetas).

Revision ID: 0077_invoice_exencion_causa
Revises: 0076_sif_events_worm
"""

import sqlalchemy as sa
from alembic import op

revision = "0077_invoice_exencion_causa"
down_revision = "0076_sif_events_worm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("exencion_causa", sa.String(2), nullable=True))


def downgrade() -> None:
    op.drop_column("invoices", "exencion_causa")
