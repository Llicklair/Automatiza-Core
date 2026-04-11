"""Add DocumentEmbeddings

Revision ID: 85d22b01f159
Revises: 480048dde7b6
Create Date: 2026-02-26 04:42:00.624759

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "85d22b01f159"
down_revision: str | None = "480048dde7b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_pgvector(connection) -> bool:
    """Comprueba si la extensión vector de pgvector está disponible en esta instalación de PostgreSQL."""
    try:
        result = connection.execute(
            sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
        )
        return result.fetchone() is not None
    except Exception:
        return False


def upgrade() -> None:
    bind = op.get_bind()

    # Intentar activar pgvector si está disponible
    pgvector_available = _has_pgvector(bind)
    if pgvector_available:
        try:
            bind.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception:
            pgvector_available = False

    if pgvector_available:
        # Usar tipo VECTOR nativo de pgvector
        import pgvector.sqlalchemy

        embedding_col = sa.Column(
            "embedding", pgvector.sqlalchemy.vector.VECTOR(dim=768), nullable=True
        )
    else:
        # Fallback: almacenar como TEXT (JSON serializado del vector)
        # La funcionalidad de embeddings estará degradada pero la app arrancará
        embedding_col = sa.Column("embedding", sa.Text(), nullable=True)

    op.create_table(
        "document_embeddings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("chunk_index", sa.String(), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=False),
        embedding_col,
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_document_embeddings_document_id"),
        "document_embeddings",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_embeddings_tenant_id"), "document_embeddings", ["tenant_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_document_embeddings_tenant_id"), table_name="document_embeddings")
    op.drop_index(op.f("ix_document_embeddings_document_id"), table_name="document_embeddings")
    op.drop_table("document_embeddings")
