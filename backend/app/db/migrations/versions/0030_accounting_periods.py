"""Crear tabla accounting_periods para cierre contable mensual/trimestral.

Permite congelar un periodo (mes o trimestre) una vez presentado el modelo
fiscal y aprobada la contabilidad. Una vez cerrado, los endpoints de write
sobre journal_entries del periodo deben rechazar la operación.

Revision ID: 0030_accounting_periods
Revises: 0029_aiemployee_contract
"""

from alembic import op

revision = "0030_accounting_periods"
down_revision = "0029_aiemployee_contract"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS accounting_periods (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            year INTEGER NOT NULL,
            kind VARCHAR(16) NOT NULL,           -- 'month' | 'quarter' | 'year'
            period_index INTEGER NOT NULL,       -- 1..12 (mes), 1..4 (trimestre), 0 (año)
            status VARCHAR(16) NOT NULL DEFAULT 'closed',  -- 'closed' | 'reopened'
            closed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            closed_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            reopened_at TIMESTAMP WITH TIME ZONE,
            reopened_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            reopen_reason VARCHAR(500),
            notes VARCHAR(500),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_accounting_periods_tenant_id ON accounting_periods(tenant_id)")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_accounting_periods_unique
        ON accounting_periods(tenant_id, year, kind, period_index)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS accounting_periods CASCADE")
