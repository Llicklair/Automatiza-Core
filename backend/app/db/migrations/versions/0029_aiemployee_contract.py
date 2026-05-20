"""Contrato mínimo del AIEmployee custom — capacidades verificables.

Para que un AIEmployee custom justifique existir frente a un default +
system_prompt_addendum, debe declarar al menos 2 de 4 capacidades:

  - `scope` (JSONB)             — filtro persistente de qué entidades ve el
                                   empleado: {clients, categories, filters}.
  - `memory_enabled` (Bool)     — habilita memoria persistente (tabla
                                   employee_memory se introducirá en una
                                   migración posterior cuando se implemente).
  - `knowledge_enabled` (Bool)  — habilita knowledge base privada (filtro RAG
                                   por employee_id, sin tabla nueva: campo
                                   employee_id en document_embeddings).
  - `workflows` (JSONB)         — rutinas predefinidas: [{name, cron, steps}].

La aplicación del "≥2 de 4" se hace en la capa de servicios al crear el
empleado, no a nivel BD: las 4 columnas son nullable porque builtins no las
necesitan.

Revision ID: 0029_aiemployee_contract
Revises: 0028_clients_unique_nif
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0029_aiemployee_contract"
down_revision = "0028_clients_unique_nif"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    json_type = JSONB if is_pg else sa.JSON

    op.add_column(
        "ai_employees",
        sa.Column("scope", json_type, nullable=True),
    )
    op.add_column(
        "ai_employees",
        sa.Column(
            "memory_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "ai_employees",
        sa.Column(
            "knowledge_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "ai_employees",
        sa.Column("workflows", json_type, nullable=True),
    )

    # Drop server_default tras backfill: la app gestiona el valor.
    if is_pg:
        op.alter_column("ai_employees", "memory_enabled", server_default=None)
        op.alter_column("ai_employees", "knowledge_enabled", server_default=None)


def downgrade() -> None:
    op.drop_column("ai_employees", "workflows")
    op.drop_column("ai_employees", "knowledge_enabled")
    op.drop_column("ai_employees", "memory_enabled")
    op.drop_column("ai_employees", "scope")
