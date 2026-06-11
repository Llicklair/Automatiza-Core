"""Tabla scheduled_post_metrics — analítica de posts de marketing.

Snapshot diario de métricas de engagement (impresiones, alcance, likes,
comentarios, shares, clics) por post publicado. Una fila por (post, día).
"""

import sqlalchemy as sa
from alembic import op

revision = "0057_scheduled_post_metrics"
down_revision = "0056_idempotency_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scheduled_post_metrics",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "scheduled_post_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("scheduled_posts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reach", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("likes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("shares", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("scheduled_post_id", "metric_date", name="uq_post_metric_day"),
    )
    op.create_index(
        "ix_scheduled_post_metrics_tenant_id", "scheduled_post_metrics", ["tenant_id"]
    )
    op.create_index(
        "ix_scheduled_post_metrics_scheduled_post_id",
        "scheduled_post_metrics",
        ["scheduled_post_id"],
    )


def downgrade() -> None:
    op.drop_table("scheduled_post_metrics")
