"""add_tenant_llm_config

Revision ID: c1d2e3f4a5b6
Revises: d8e9f0a1b2c3
Create Date: 2026-03-14

"""
from alembic import op
import sqlalchemy as sa

revision = "c1d2e3f4a5b6"
down_revision = "d8e9f0a1b2c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_llm_configs",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, unique=True),
        sa.Column("active_llm_provider", sa.String(50), nullable=False, server_default="gemini"),
        sa.Column("active_embeddings_provider", sa.String(50), nullable=False, server_default="local"),
        sa.Column("encrypted_keys", sa.Text),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_tenant_llm_configs_tenant_id", "tenant_llm_configs", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_tenant_llm_configs_tenant_id", "tenant_llm_configs")
    op.drop_table("tenant_llm_configs")
