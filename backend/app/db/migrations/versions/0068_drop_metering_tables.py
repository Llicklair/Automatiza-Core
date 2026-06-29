"""Drop metering tables (interaction_usage, cron_execution_usage).

La feature de metering por uso (OPS.OVR / OPS.CRON) quedo sin cablear: el servicio
`billing/metering` y sus modelos no tenian ningun llamador de produccion (solo
tests) y se eliminaron. Estas tablas quedaban huerfanas -> se dropean.

Reversible: el downgrade recrea exactamente el esquema original de 0015_metering.

Revision ID: 0068_drop_metering_tables
Revises: 0067_idempotency_unique_constraints
"""

from alembic import op

revision = "0068_drop_metering_tables"
down_revision = "0067_idempotency_unique_constraints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_cron_usage_tenant_year_month")
    op.execute("DROP INDEX IF EXISTS ix_interaction_usage_tenant_year_month")
    op.execute("DROP TABLE IF EXISTS cron_execution_usage")
    op.execute("DROP TABLE IF EXISTS interaction_usage")


def downgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS interaction_usage (
            id BIGSERIAL PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            year INT NOT NULL,
            month INT NOT NULL CHECK (month BETWEEN 1 AND 12),
            count INT NOT NULL DEFAULT 0,
            overage_count INT NOT NULL DEFAULT 0,
            last_recorded_at TIMESTAMP WITH TIME ZONE,
            UNIQUE (tenant_id, year, month)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_interaction_usage_tenant_year_month "
        "ON interaction_usage(tenant_id, year, month)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cron_execution_usage (
            id BIGSERIAL PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            year INT NOT NULL,
            month INT NOT NULL CHECK (month BETWEEN 1 AND 12),
            count INT NOT NULL DEFAULT 0,
            last_recorded_at TIMESTAMP WITH TIME ZONE,
            UNIQUE (tenant_id, year, month)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_cron_usage_tenant_year_month "
        "ON cron_execution_usage(tenant_id, year, month)"
    )
