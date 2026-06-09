"""Marketing: scheduled_posts.retry_count para reintentos con backoff.

Revision ID: 0050_post_retry_count
Revises: 0049_email_marketing
"""

from alembic import op

revision = "0050_post_retry_count"
down_revision = "0049_email_marketing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE scheduled_posts "
        "ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE scheduled_posts DROP COLUMN IF EXISTS retry_count")
