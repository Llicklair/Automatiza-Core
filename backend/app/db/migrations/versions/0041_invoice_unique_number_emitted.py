"""Índice UNIQUE parcial del número de factura para las emitidas.

RD 1619/2012 Art. 6.1 — numeración correlativa por serie sin duplicados. Hasta
ahora la unicidad se garantizaba solo a nivel de aplicación (advisory lock en la
numeración automática + guarda del número manual). Este índice la blinda en BD.

Es PARCIAL a propósito: cubre únicamente las facturas que emitimos nosotros
(`invoice_type IN ('issued','rectificativa')`). Las recibidas llevan el número
del proveedor —que puede repetirse entre proveedores y coincidir con el nuestro—
así que quedan fuera del índice (p.ej. una venta y una compra pueden compartir el
string "A2026-0005" legítimamente).

Revision ID: 0041_invoice_unique_number_emitted
Revises: 0040_invoice_rectificativa
"""

import sqlalchemy as sa
from alembic import op

revision = "0041_invoice_unique_number_emitted"
down_revision = "0040_invoice_rectificativa"
branch_labels = None
depends_on = None

INDEX_NAME = "uq_invoices_tenant_number_emitted"


def upgrade() -> None:
    op.create_index(
        INDEX_NAME,
        "invoices",
        ["tenant_id", "invoice_number"],
        unique=True,
        postgresql_where=sa.text("invoice_type IN ('issued', 'rectificativa')"),
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="invoices")
