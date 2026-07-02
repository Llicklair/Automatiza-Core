"""Persistencia del consumo LLM agregado (snapshot del tracker en memoria).

Tabla `llm_usage_monthly`: agregados absolutos por
(tenant_id, month, agent, provider). El backend la vuelca al apagar /
periódicamente y la recarga al arrancar, para que el dashboard de consumo
sobreviva a los reinicios del backend de escritorio.

Revision ID: 0037_llm_usage_monthly
Revises: 0036_signed_documents
"""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0037_llm_usage_monthly"
down_revision = "0036_signed_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    uuid_type = UUID(as_uuid=True) if is_pg else sa.String(36)

    op.create_table(
        "llm_usage_monthly",
        sa.Column("id", uuid_type, primary_key=True, default=uuid.uuid4),
        sa.Column(
            "tenant_id",
            uuid_type,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("month", sa.String(7), nullable=False),
        sa.Column("agent", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_in", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("tokens_out", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "month", "agent", "provider", name="uq_llm_usage_monthly_dims"),
    )
    op.create_index("ix_llm_usage_monthly_tenant_id", "llm_usage_monthly", ["tenant_id"])
    op.create_index("ix_llm_usage_monthly_month", "llm_usage_monthly", ["month"])


def downgrade() -> None:
    op.drop_index("ix_llm_usage_monthly_month", table_name="llm_usage_monthly")
    op.drop_index("ix_llm_usage_monthly_tenant_id", table_name="llm_usage_monthly")
    op.drop_table("llm_usage_monthly")
