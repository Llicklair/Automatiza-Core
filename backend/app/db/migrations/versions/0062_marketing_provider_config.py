"""Marketing BYO Zernio: marketing_provider_config (multi-cuenta por tenant) +
social_accounts.provider_config_id.

Revision ID: 0062_marketing_provider_config
Revises: 0061_document_embeddings_fk
"""

from alembic import op

revision = "0062_marketing_provider_config"
down_revision = "0061_document_embeddings_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS marketing_provider_config (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id           UUID NOT NULL REFERENCES tenants(id),
            provider            VARCHAR(50) NOT NULL DEFAULT 'zernio',
            label               VARCHAR(255),
            api_key             TEXT,
            default_profile_id  VARCHAR(255),
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_marketing_provider_config_tenant_id "
        "ON marketing_provider_config(tenant_id)"
    )
    # Cada cuenta social recuerda por qué cuenta de Zernio (email/key) se conectó.
    op.execute(
        "ALTER TABLE social_accounts "
        "ADD COLUMN IF NOT EXISTS provider_config_id UUID "
        "REFERENCES marketing_provider_config(id) ON DELETE SET NULL"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE social_accounts DROP COLUMN IF EXISTS provider_config_id")
    op.execute("DROP TABLE IF EXISTS marketing_provider_config")
