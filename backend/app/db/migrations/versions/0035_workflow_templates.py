"""Marketplace de workflows (F3.10) — plantillas curadas reutilizables.

Cada `WorkflowTemplate` empaqueta la definición de un workflow (trigger
+ pasos) en un formato listo para instanciar como `Workflow` real del
tenant. Permite compartir entre tenants sin centralizar datos del
negocio — sólo viajan la lógica del workflow y su metadata.

Revision ID: 0035_workflow_templates
Revises: 0034_reconciliation_rejections
"""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0035_workflow_templates"
down_revision = "0034_reconciliation_rejections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    json_type = JSONB if is_pg else sa.JSON
    uuid_type = UUID(as_uuid=True) if is_pg else sa.String(36)

    op.create_table(
        "workflow_templates",
        sa.Column("id", uuid_type, primary_key=True, default=uuid.uuid4),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(60), nullable=False),
        sa.Column("author", sa.String(120), nullable=True),
        sa.Column("trigger_type", sa.String(50), nullable=False),
        sa.Column("trigger_config", json_type, nullable=False),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("action_config", json_type, nullable=False),
        sa.Column("execution_mode", sa.String(20), nullable=False, server_default="reasoning"),
        sa.Column("compiled_steps", json_type, nullable=True),
        sa.Column("tags", json_type, nullable=True),
        sa.Column("is_official", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("downloads_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_workflow_templates_category", "workflow_templates", ["category"]
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_templates_category", table_name="workflow_templates")
    op.drop_table("workflow_templates")
