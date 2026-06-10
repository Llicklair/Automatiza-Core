"""Tabla idempotency_keys — claves de idempotencia persistentes del scheduler.

Antes vivían en memoria: un reinicio dentro de la ventana del cron podía
duplicar jobs no idempotentes (facturas recurrentes → incidente Verifactu).
"""

import sqlalchemy as sa
from alembic import op

revision = "0056_idempotency_keys"
down_revision = "0055_work_sched_uq"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "idempotency_keys",
        sa.Column("key", sa.String(255), primary_key=True),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_idempotency_keys_expires_at", "idempotency_keys", ["expires_at"])


def downgrade() -> None:
    op.drop_table("idempotency_keys")
