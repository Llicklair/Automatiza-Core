"""Folio correlativo de documentos de gestoría — hr_documents.doc_number.

Asigna una referencia única por tenant y año al aprobar un documento laboral
(ej. DOC-2026-0001), para trazabilidad y referencia legal.
"""

import sqlalchemy as sa
from alembic import op

revision = "0058_hr_document_number"
down_revision = "0057_scheduled_post_metrics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("hr_documents", sa.Column("doc_number", sa.String(40), nullable=True))
    op.create_index("ix_hr_documents_doc_number", "hr_documents", ["doc_number"])


def downgrade() -> None:
    op.drop_index("ix_hr_documents_doc_number", table_name="hr_documents")
    op.drop_column("hr_documents", "doc_number")
