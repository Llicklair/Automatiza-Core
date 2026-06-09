"""Marketing: social_accounts, marketing_campaigns, scheduled_posts.

Revision ID: 0048_marketing_social
Revises: 0047_po_received_quantity
"""

from alembic import op

revision = "0048_marketing_social"
down_revision = "0047_po_received_quantity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS social_accounts (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID NOT NULL REFERENCES tenants(id),
            platform        VARCHAR(50) NOT NULL,
            account_id      VARCHAR(255) NOT NULL,
            account_name    VARCHAR(255),
            access_token    TEXT NOT NULL,
            refresh_token   TEXT,
            token_expires_at TIMESTAMPTZ,
            is_active       BOOLEAN NOT NULL DEFAULT TRUE,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_social_accounts_tenant_id ON social_accounts(tenant_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS marketing_campaigns (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id   UUID NOT NULL REFERENCES tenants(id),
            name        VARCHAR(255) NOT NULL,
            description TEXT,
            start_date  TIMESTAMPTZ,
            end_date    TIMESTAMPTZ,
            is_active   BOOLEAN NOT NULL DEFAULT TRUE,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_marketing_campaigns_tenant_id ON marketing_campaigns(tenant_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_posts (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id           UUID NOT NULL REFERENCES tenants(id),
            campaign_id         UUID REFERENCES marketing_campaigns(id) ON DELETE SET NULL,
            social_account_id   UUID NOT NULL REFERENCES social_accounts(id),
            platform            VARCHAR(50) NOT NULL,
            content             TEXT NOT NULL,
            image_url           TEXT,
            scheduled_at        TIMESTAMPTZ,
            published_at        TIMESTAMPTZ,
            status              VARCHAR(50) NOT NULL DEFAULT 'draft',
            platform_post_id    VARCHAR(255),
            error_message       TEXT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_scheduled_posts_tenant_id ON scheduled_posts(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_scheduled_posts_status ON scheduled_posts(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_scheduled_posts_scheduled_at ON scheduled_posts(scheduled_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS scheduled_posts")
    op.execute("DROP TABLE IF EXISTS marketing_campaigns")
    op.execute("DROP TABLE IF EXISTS social_accounts")
