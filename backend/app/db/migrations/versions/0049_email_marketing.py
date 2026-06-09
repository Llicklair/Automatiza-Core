"""Email marketing: email_templates, email_campaigns, email_campaign_recipients.

Revision ID: 0049_email_marketing
Revises: 0048_marketing_social
"""

from alembic import op

revision = "0049_email_marketing"
down_revision = "0048_marketing_social"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS email_templates (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id   UUID NOT NULL REFERENCES tenants(id),
            name        VARCHAR(255) NOT NULL,
            subject     VARCHAR(500) NOT NULL,
            html_body   TEXT NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_email_templates_tenant_id ON email_templates(tenant_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS email_campaigns (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id     UUID NOT NULL REFERENCES tenants(id),
            template_id   UUID REFERENCES email_templates(id) ON DELETE SET NULL,
            name          VARCHAR(255) NOT NULL,
            subject       VARCHAR(500) NOT NULL,
            html_body     TEXT NOT NULL,
            status        VARCHAR(50) NOT NULL DEFAULT 'draft',
            scheduled_at  TIMESTAMPTZ,
            sent_at       TIMESTAMPTZ,
            total_count   INTEGER NOT NULL DEFAULT 0,
            sent_count    INTEGER NOT NULL DEFAULT 0,
            failed_count  INTEGER NOT NULL DEFAULT 0,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at    TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_email_campaigns_tenant_id ON email_campaigns(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_email_campaigns_status ON email_campaigns(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_email_campaigns_scheduled_at ON email_campaigns(scheduled_at)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS email_campaign_recipients (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            campaign_id  UUID NOT NULL REFERENCES email_campaigns(id) ON DELETE CASCADE,
            email        VARCHAR(255) NOT NULL,
            name         VARCHAR(255),
            status       VARCHAR(50) NOT NULL DEFAULT 'pending',
            sent_at      TIMESTAMPTZ,
            error_message TEXT
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_ecr_campaign_id ON email_campaign_recipients(campaign_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS email_campaign_recipients")
    op.execute("DROP TABLE IF EXISTS email_campaigns")
    op.execute("DROP TABLE IF EXISTS email_templates")
