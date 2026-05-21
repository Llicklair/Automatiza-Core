"""Templates de proveedor + cache de escaneos para OCR con aprendizaje.

Capacidad F2.5 — Reducir consumo LLM en facturas recurrentes:

  - `invoice_scan_cache`         — Dedupe estricto por SHA-256 del archivo.
                                    Si el mismo PDF vuelve a entrar, se
                                    devuelve la extracción guardada sin
                                    llamar al modelo.

  - `supplier_invoice_templates` — Memoria por (tenant_id, supplier_nif).
                                    Guarda la última extracción para usarla
                                    como few-shot en el prompt y los
                                    overrides aprendidos del usuario
                                    (tax_percentage habitual, renombrados
                                    de descripción, etc.).

Revision ID: 0033_supplier_invoice_templates
Revises: 0032_employee_memory_and_rag_scope
"""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0033_supplier_invoice_templates"
down_revision = "0032_employee_memory_and_rag_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    json_type = JSONB if is_pg else sa.JSON
    uuid_type = UUID(as_uuid=True) if is_pg else sa.String(36)

    op.create_table(
        "invoice_scan_cache",
        sa.Column("id", uuid_type, primary_key=True, default=uuid.uuid4),
        sa.Column(
            "tenant_id",
            uuid_type,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(50), nullable=False),
        sa.Column("extracted_data", json_type, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("tenant_id", "file_hash", name="uq_invoice_scan_cache_tenant_hash"),
    )

    op.create_table(
        "supplier_invoice_templates",
        sa.Column("id", uuid_type, primary_key=True, default=uuid.uuid4),
        sa.Column(
            "tenant_id",
            uuid_type,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("supplier_nif", sa.String(32), nullable=False),
        sa.Column("supplier_name", sa.String(255), nullable=True),
        sa.Column("default_tax_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("description_overrides", json_type, nullable=True),
        sa.Column("last_extraction", json_type, nullable=True),
        sa.Column("extractions_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_amount_total", sa.Numeric(12, 2), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint(
            "tenant_id", "supplier_nif", name="uq_supplier_template_tenant_nif"
        ),
    )
    op.create_index(
        "ix_supplier_template_tenant_nif",
        "supplier_invoice_templates",
        ["tenant_id", "supplier_nif"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_supplier_template_tenant_nif", table_name="supplier_invoice_templates"
    )
    op.drop_table("supplier_invoice_templates")
    op.drop_table("invoice_scan_cache")
