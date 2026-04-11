"""add_generated_uis_table

Revision ID: g1e2n3e4r5a6
Revises: h0m1e2r3g4e5
Create Date: 2026-04-08

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "g1e2n3e4r5a6"
down_revision = "h0m1e2r3g4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "generated_uis",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("content_html", sa.Text, nullable=False),
        sa.Column("is_pinned", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("metadata_json", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_generated_uis_tenant_id", "generated_uis", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_generated_uis_tenant_id", table_name="generated_uis")
    op.drop_table("generated_uis")
