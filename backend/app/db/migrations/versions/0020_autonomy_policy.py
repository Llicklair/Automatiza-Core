"""Create autonomy_policy — política de autonomía por dominio (SEC.AUT).

SEC.AUT — cada tenant configura el nivel de autonomía con el que sus
agentes ejecutan acciones por dominio. Tres modos:

  - `AUTO`    — el agente actúa sin confirmación.
  - `CONFIRM` — el agente prepara la acción pero requiere clic humano.
  - `MANUAL`  — el agente solo sugiere; el usuario ejecuta manualmente.

Defaults consensuados (Ronda 30 §54):
  - `banking_write` = MANUAL
  - `accounting`    = CONFIRM
  - `marketing`     = CONFIRM (beta)
  - `recruitment`   = CONFIRM (beta)
  - resto           = AUTO

La fila se crea bajo demanda — la ausencia equivale al default del dominio.

Revision ID: 0020_autonomy_policy
Revises: 0019_tenant_regap_status
"""

from alembic import op

revision = "0020_autonomy_policy"
down_revision = "0019_tenant_regap_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS autonomy_policy (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            domain VARCHAR(64) NOT NULL,
            mode VARCHAR(16) NOT NULL,
            updated_by UUID,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_autonomy_policy_tenant_domain " "ON autonomy_policy(tenant_id, domain)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_autonomy_policy_tenant_domain")
    op.execute("DROP TABLE IF EXISTS autonomy_policy")
