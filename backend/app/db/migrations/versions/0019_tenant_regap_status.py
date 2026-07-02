"""Create tenant_regap_status — estado del apoderamiento REGAP por tenant.

PRES.REG — wizard onboarding REGAP (Registro de Apoderamientos AEAT).
Cada tenant tiene un único estado de apoderamiento que recorre:

  not_started → identifying → cert_pending → power_granted → verified
                                                 │
                                                 └→ rejected (excepcional)

`auth_method` indica la rama elegida (clave_pin | clave_permanente |
cert_fnmt). `apoderado_nif` guarda el NIF de AutomatizaCore S.L. al que
el cliente apodera (cargado del setting tenant). `verified_at` se setea
cuando la consulta REGAP confirma el alta.

Revision ID: 0019_tenant_regap_status
Revises: 0018_verifactu_backfill_flag
"""

from alembic import op

revision = "0019_tenant_regap_status"
down_revision = "0018_verifactu_backfill_flag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tenant_regap_status (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL UNIQUE,
            status VARCHAR(32) NOT NULL DEFAULT 'not_started',
            auth_method VARCHAR(32),
            apoderado_nif VARCHAR(20),
            apoderado_nombre VARCHAR(200),
            verify_payload TEXT,
            verified_at TIMESTAMP WITH TIME ZONE,
            rejected_reason VARCHAR(500),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_tenant_regap_status_tenant " "ON tenant_regap_status(tenant_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_tenant_regap_status_tenant")
    op.execute("DROP TABLE IF EXISTS tenant_regap_status")
