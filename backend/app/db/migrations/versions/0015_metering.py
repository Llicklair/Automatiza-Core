"""OPS.OVR + OPS.CRON — Tablas de metering para billing + cron caps.

`interaction_usage`: 1 fila por (tenant, año, mes). Incrementa con cada
invocación de `run_agent()`. Trigger los soft cap/banner 450/500 y el cobro
de overage a 0,05€ + IVA por interacción adicional (hard cap 1000).

`cron_execution_usage`: 1 fila por (tenant, año, mes). Incrementa con cada
ejecución de workflow cron. Caps escalados por tier — el helper Python
valida contra `subscription_tier` + nº empresas activas en gestoría.

Revision ID: 0015_metering
Revises: 0014_telemetry_opt_out
"""

from alembic import op

revision = "0015_metering"
down_revision = "0014_telemetry_opt_out"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
        "CREATE INDEX IF NOT EXISTS ix_cron_usage_tenant_year_month " "ON cron_execution_usage(tenant_id, year, month)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_cron_usage_tenant_year_month")
    op.execute("DROP INDEX IF EXISTS ix_interaction_usage_tenant_year_month")
    op.execute("DROP TABLE IF EXISTS cron_execution_usage")
    op.execute("DROP TABLE IF EXISTS interaction_usage")
