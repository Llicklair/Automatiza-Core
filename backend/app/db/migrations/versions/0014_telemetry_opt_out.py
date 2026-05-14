"""AI.REV — Crea telemetry_opt_out (RGPD Art. 17 derecho de supresión telemetría).

Revision ID: 0014_telemetry_opt_out
Revises: 0013_fiscal_approval_log
"""

from alembic import op

revision = "0014_telemetry_opt_out"
down_revision = "0013_fiscal_approval_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetry_opt_out (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL UNIQUE REFERENCES tenants(id) ON DELETE CASCADE,
            requested_by UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_telemetry_opt_out_tenant "
        "ON telemetry_opt_out(tenant_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_telemetry_opt_out_tenant")
    op.execute("DROP TABLE IF EXISTS telemetry_opt_out")
