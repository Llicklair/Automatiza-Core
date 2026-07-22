"""Vertical tintorería T1: registro de la entrega en el albarán-resguardo.

`delivered_at` / `delivered_by` en delivery_notes: quién y cuándo entregó el
encargo cuando el cliente vuelve con el resguardo. Los estados nuevos
(recibido/en_proceso/listo/anulado) no requieren cambio de esquema (String).

Revision ID: 0078_albaran_tintoreria
Revises: 0077_invoice_exencion_causa
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0078_albaran_tintoreria"
down_revision = "0077_invoice_exencion_causa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("delivery_notes", sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "delivery_notes",
        sa.Column("delivered_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("delivery_notes", "delivered_by")
    op.drop_column("delivery_notes", "delivered_at")
