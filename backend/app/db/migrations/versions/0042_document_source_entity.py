"""Procedencia y enlace a entidad en `tenant_documents`.

Distingue los documentos que el ERP GENERA (PDF de factura/nómina/informe,
`source='generated'`) de los EXTERNOS subidos/escaneados (`source='uploaded'`),
y añade un vínculo opaco (`entity_type` + `entity_id`) a la entidad del ERP que
el documento refleja o de la que procede.

Esto (a) permite mostrar un PDF como "reflejo de Factura X" en vez de un fichero
suelto, y (b) da idempotencia a la asimilación automática documento→ERP: lo ya
importado queda enlazado y no se reprocesa.

Las filas existentes se quedan con `source='uploaded'` (default), que es el
comportamiento conservador (no se asume que un documento previo sea un reflejo).

Revision ID: 0042_document_source_entity
Revises: 0041_invoice_unique_number_emitted
"""

import sqlalchemy as sa
from alembic import op

revision = "0042_document_source_entity"
down_revision = "0041_invoice_unique_number_emitted"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenant_documents",
        sa.Column("source", sa.String(20), nullable=False, server_default="uploaded"),
    )
    op.add_column(
        "tenant_documents",
        sa.Column("entity_type", sa.String(50), nullable=True),
    )
    op.add_column(
        "tenant_documents",
        sa.Column("entity_id", sa.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_tenant_documents_source", "tenant_documents", ["source"])
    op.create_index("ix_tenant_documents_entity_id", "tenant_documents", ["entity_id"])


def downgrade() -> None:
    op.drop_index("ix_tenant_documents_entity_id", table_name="tenant_documents")
    op.drop_index("ix_tenant_documents_source", table_name="tenant_documents")
    op.drop_column("tenant_documents", "entity_id")
    op.drop_column("tenant_documents", "entity_type")
    op.drop_column("tenant_documents", "source")
