"""Crea sif_events: registro de eventos del SIF (RD 1007/2023 Art. 14).

Cadena append-only por tenant encadenada por huella SHA-256, misma integridad que
los registros de facturación.

Revision ID: 0074_sif_events
Revises: 0073_pos_session_invoice
"""

from alembic import op

revision = "0074_sif_events"
down_revision = "0073_pos_session_invoice"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE sif_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            tipo_evento VARCHAR(40) NOT NULL,
            detalle TEXT,
            huella VARCHAR(64) NOT NULL,
            huella_anterior VARCHAR(64),
            payload_canonico TEXT NOT NULL,
            fecha_hora TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_sif_events_tenant_id ON sif_events (tenant_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS sif_events")
