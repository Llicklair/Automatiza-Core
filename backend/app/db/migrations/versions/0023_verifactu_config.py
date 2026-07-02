"""Create verifactu_config — modo de remisión por tenant (FAC.MODE).

RD 1007/2023 distingue dos modos operativos:
  - `voluntary`     — modalidad VERI*FACTU: cada factura se remite a AEAT
                       al emitirse (firma XAdES + acuse).
  - `no_remission`  — SIF puro: el sistema genera la cadena `huella` y la
                       conserva localmente, sin envío. La AEAT puede
                       requerir la información a posteriori.

El default seguro hasta DEC.14 (alta colaborador social) es `no_remission`
— sin alta no podemos remitir telemáticamente aunque el cliente lo quiera.

Revision ID: 0023_verifactu_config
Revises: 0022_notifications
"""

from alembic import op

revision = "0023_verifactu_config"
down_revision = "0022_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS verifactu_config (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL UNIQUE,
            mode VARCHAR(32) NOT NULL DEFAULT 'no_remission',
            updated_by UUID,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_verifactu_config_tenant " "ON verifactu_config(tenant_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_verifactu_config_tenant")
    op.execute("DROP TABLE IF EXISTS verifactu_config")
