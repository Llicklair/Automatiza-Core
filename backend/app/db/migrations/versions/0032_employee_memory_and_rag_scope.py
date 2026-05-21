"""Memoria persistente del AIEmployee + filtro RAG por employee.

Cierra dos de las cuatro capacidades del contrato del AIEmployee custom
declaradas en la migración 0029_aiemployee_contract:

  - `memory_enabled`     → tabla `employee_memory` (key/value JSONB con
                            unicidad (employee_id, key)).
  - `knowledge_enabled`  → columna `employee_id` (nullable) en
                            `document_embeddings`. NULL = base de
                            conocimiento del tenant accesible por todos los
                            empleados; valor → embedding privado del empleado.

Las otras dos capacidades (`scope`, `workflows`) no requieren tabla nueva:
ya viven como JSONB en `ai_employees` desde 0029.

Revision ID: 0032_employee_memory_and_rag_scope
Revises: 0031_aeat_presentation
"""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0032_employee_memory_and_rag_scope"
down_revision = "0031_aeat_presentation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    json_type = JSONB if is_pg else sa.JSON
    uuid_type = UUID(as_uuid=True) if is_pg else sa.String(36)

    op.create_table(
        "employee_memory",
        sa.Column("id", uuid_type, primary_key=True, default=uuid.uuid4),
        sa.Column(
            "tenant_id",
            uuid_type,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "employee_id",
            uuid_type,
            sa.ForeignKey("ai_employees.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key", sa.String(160), nullable=False),
        sa.Column("value", json_type, nullable=False),
        sa.Column("importance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("employee_id", "key", name="uq_employee_memory_employee_key"),
    )
    op.create_index(
        "ix_employee_memory_tenant_employee",
        "employee_memory",
        ["tenant_id", "employee_id"],
    )

    op.add_column(
        "document_embeddings",
        sa.Column(
            "employee_id",
            uuid_type,
            sa.ForeignKey("ai_employees.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_document_embeddings_employee_id",
        "document_embeddings",
        ["employee_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_document_embeddings_employee_id", table_name="document_embeddings")
    op.drop_column("document_embeddings", "employee_id")
    op.drop_index("ix_employee_memory_tenant_employee", table_name="employee_memory")
    op.drop_table("employee_memory")
