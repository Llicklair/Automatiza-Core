"""Add missing indexes for performance

Revision ID: f1a2b3c4d5e6
Revises: e1f2a3b4c5d6
Create Date: 2026-03-11
"""
from alembic import op

revision = "f1a2b3c4d5e6"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade():
    # InvoiceLine.product_id — frecuente en JOINs de líneas de factura
    op.create_index("ix_invoice_lines_product_id", "invoice_lines", ["product_id"])
    # Activity — búsquedas por client_id y opportunity_id
    op.create_index("ix_activities_client_id", "activities", ["client_id"])
    op.create_index("ix_activities_opportunity_id", "activities", ["opportunity_id"])
    # Índice compuesto tenant_id + created_at para filtros comunes en invoices
    op.create_index("ix_invoices_tenant_created", "invoices", ["tenant_id", "created_at"])
    # Índice compuesto tenant_id + created_at para tasks
    op.create_index("ix_tasks_tenant_created", "tasks", ["tenant_id", "created_at"])


def downgrade():
    op.drop_index("ix_tasks_tenant_created", "tasks")
    op.drop_index("ix_invoices_tenant_created", "invoices")
    op.drop_index("ix_activities_opportunity_id", "activities")
    op.drop_index("ix_activities_client_id", "activities")
    op.drop_index("ix_invoice_lines_product_id", "invoice_lines")
