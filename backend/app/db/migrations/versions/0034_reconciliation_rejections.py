"""Rechazos persistentes de sugerencias de conciliación bancaria (F2.6).

Cuando el usuario descarta una sugerencia tx↔invoice, el par queda
registrado y deja de aparecer en futuras consultas. Imprescindible para
que el motor sea de fiar — sin esto, las mismas sugerencias incorrectas
volverían a aparecer cada vez.

Revision ID: 0034_reconciliation_rejections
Revises: 0033_supplier_invoice_templates
"""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0034_reconciliation_rejections"
down_revision = "0033_supplier_invoice_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    uuid_type = UUID(as_uuid=True) if is_pg else sa.String(36)

    op.create_table(
        "reconciliation_rejections",
        sa.Column("id", uuid_type, primary_key=True, default=uuid.uuid4),
        sa.Column(
            "tenant_id",
            uuid_type,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("transaction_id", uuid_type, nullable=False),
        sa.Column("invoice_id", uuid_type, nullable=False),
        sa.Column("reason", sa.String(200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "transaction_id",
            "invoice_id",
            name="uq_reconciliation_rejection_pair",
        ),
    )
    op.create_index(
        "ix_reconciliation_rejection_tenant",
        "reconciliation_rejections",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_reconciliation_rejection_tenant",
        table_name="reconciliation_rejections",
    )
    op.drop_table("reconciliation_rejections")
