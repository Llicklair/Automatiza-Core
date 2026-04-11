"""add document_templates table

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-03-27 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f3a4b5c6d7e8"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("template_type", sa.String(20), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("layout_style", sa.String(20), nullable=False, server_default="modern"),
        sa.Column("accent_color", sa.String(7), nullable=False, server_default="#6366f1"),
        sa.Column("font_family", sa.String(20), nullable=False, server_default="helvetica"),
        sa.Column("logo_position", sa.String(10), nullable=False, server_default="left"),
        sa.Column("header_style", sa.String(20), nullable=False, server_default="color_band"),
        sa.Column("table_style", sa.String(20), nullable=False, server_default="striped"),
        sa.Column("footer_text", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_templates_tenant_id", "document_templates", ["tenant_id"])
    op.create_index(
        "ix_document_templates_type", "document_templates", ["tenant_id", "template_type"]
    )


def downgrade() -> None:
    op.drop_index("ix_document_templates_type", table_name="document_templates")
    op.drop_index("ix_document_templates_tenant_id", table_name="document_templates")
    op.drop_table("document_templates")
