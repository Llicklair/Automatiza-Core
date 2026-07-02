"""Firma eIDAS con AutoFirma del Estado (F3.11).

Registra los documentos firmados por el usuario mediante AutoFirma
(protocolo `afirma://`). El XML/PDF firmado se guarda en disco como
adjunto del `TenantDocument` correspondiente, y `signed_documents`
mantiene la metadata para auditoría: NIF firmante, sello de tiempo
TSA, formato (PAdES/XAdES/CAdES), hash original.

Revision ID: 0036_signed_documents
Revises: 0035_workflow_templates
"""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0036_signed_documents"
down_revision = "0035_workflow_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    json_type = JSONB if is_pg else sa.JSON
    uuid_type = UUID(as_uuid=True) if is_pg else sa.String(36)

    op.create_table(
        "signed_documents",
        sa.Column("id", uuid_type, primary_key=True, default=uuid.uuid4),
        sa.Column(
            "tenant_id",
            uuid_type,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            uuid_type,
            sa.ForeignKey("tenant_documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("session_token", sa.String(64), nullable=False, unique=True),
        sa.Column("signature_format", sa.String(20), nullable=False),  # PAdES | XAdES | CAdES
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("original_hash", sa.String(64), nullable=False),
        sa.Column("signed_hash", sa.String(64), nullable=True),
        sa.Column("signer_nif", sa.String(32), nullable=True),
        sa.Column("signer_cn", sa.String(255), nullable=True),
        sa.Column("issuer_cn", sa.String(255), nullable=True),
        sa.Column("tsa_url", sa.String(255), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", json_type, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_signed_documents_tenant", "signed_documents", ["tenant_id"])
    op.create_index("ix_signed_documents_session_token", "signed_documents", ["session_token"])


def downgrade() -> None:
    op.drop_index("ix_signed_documents_session_token", table_name="signed_documents")
    op.drop_index("ix_signed_documents_tenant", table_name="signed_documents")
    op.drop_table("signed_documents")
