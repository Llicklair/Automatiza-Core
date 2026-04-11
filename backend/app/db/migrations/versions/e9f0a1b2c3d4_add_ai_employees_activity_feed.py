"""add ai_employees, agent_skills, token_ledger, activity_feed

Revision ID: e9f0a1b2c3d4
Revises: z9y8x7w6v5u4
Create Date: 2026-04-02

Tablas nuevas — completamente aditivas, no modifica ninguna tabla existente.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e9f0a1b2c3d4"
down_revision = "z9y8x7w6v5u4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- ai_employees ---
    op.create_table(
        "ai_employees",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(100), nullable=False),
        sa.Column("domain", sa.String(50), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("budget_limit_usd", sa.Numeric(10, 2), nullable=True, server_default="10.00"),
        sa.Column("status", sa.String(20), nullable=False, server_default="idle"),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_employees_tenant_id", "ai_employees", ["tenant_id"])

    # --- agent_skills ---
    op.create_table(
        "agent_skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tool_module", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["ai_employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_skills_employee_id", "agent_skills", ["employee_id"])

    # --- token_ledger ---
    op.create_table(
        "token_ledger",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=False),
        sa.Column("llm_provider", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_id"], ["ai_employees.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_token_ledger_tenant_id", "token_ledger", ["tenant_id"])
    op.create_index("ix_token_ledger_employee_id", "token_ledger", ["employee_id"])
    op.create_index("ix_token_ledger_created_at", "token_ledger", ["created_at"])

    # --- activity_feed ---
    op.create_table(
        "activity_feed",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("icon", sa.String(10), nullable=False, server_default="📋"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_id"], ["ai_employees.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activity_feed_tenant_id", "activity_feed", ["tenant_id"])
    op.create_index("ix_activity_feed_employee_id", "activity_feed", ["employee_id"])
    op.create_index("ix_activity_feed_created_at", "activity_feed", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_activity_feed_created_at", table_name="activity_feed")
    op.drop_index("ix_activity_feed_employee_id", table_name="activity_feed")
    op.drop_index("ix_activity_feed_tenant_id", table_name="activity_feed")
    op.drop_table("activity_feed")

    op.drop_index("ix_token_ledger_created_at", table_name="token_ledger")
    op.drop_index("ix_token_ledger_employee_id", table_name="token_ledger")
    op.drop_index("ix_token_ledger_tenant_id", table_name="token_ledger")
    op.drop_table("token_ledger")

    op.drop_index("ix_agent_skills_employee_id", table_name="agent_skills")
    op.drop_table("agent_skills")

    op.drop_index("ix_ai_employees_tenant_id", table_name="ai_employees")
    op.drop_table("ai_employees")
