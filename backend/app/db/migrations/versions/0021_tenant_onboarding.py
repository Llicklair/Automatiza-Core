"""Create tenant_onboarding — wizard 4 pasos de UI.ONB.

UI.ONB — onboarding wizard focado de 4 pasos:
  1. company     — alta de empresa (nombre, NIF, dirección fiscal)
  2. cert        — cert FNMT / Cl@ve (delegado a wizard PRES.REG)
  3. data        — conectar N43 / importar desde Holded / CSV
  4. use_case    — caso de uso guiado (primera factura, primera nómina...)

Un solo registro por tenant. La FSM no es estricta — el usuario puede
saltar pasos en cualquier orden o terminar prematuramente con `Skip`.
`completed_at` se setea cuando los 4 están en True o cuando el usuario
hace skip-to-end. `skipped_at` distingue "completado todo" vs "saltado".

Revision ID: 0021_tenant_onboarding
Revises: 0020_autonomy_policy
"""

from alembic import op

revision = "0021_tenant_onboarding"
down_revision = "0020_autonomy_policy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tenant_onboarding (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL UNIQUE,
            step_company BOOLEAN NOT NULL DEFAULT FALSE,
            step_cert BOOLEAN NOT NULL DEFAULT FALSE,
            step_data BOOLEAN NOT NULL DEFAULT FALSE,
            step_use_case BOOLEAN NOT NULL DEFAULT FALSE,
            completed_at TIMESTAMP WITH TIME ZONE,
            skipped_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tenant_onboarding_tenant "
        "ON tenant_onboarding(tenant_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_tenant_onboarding_tenant")
    op.execute("DROP TABLE IF EXISTS tenant_onboarding")
