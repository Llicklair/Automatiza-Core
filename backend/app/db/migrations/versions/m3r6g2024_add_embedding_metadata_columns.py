"""Add page_number, element_type, bounding_box to document_embeddings

Revision ID: m3r6g2024odl
Revises: a2b3c4d5e6f7, b2c3d4e5f6a8
Create Date: 2026-03-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers
revision = "m3r6g2024odl"
down_revision = ("a2b3c4d5e6f7", "b2c3d4e5f6a8")  # merge de ambos heads
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("document_embeddings", sa.Column("page_number", sa.Integer(), nullable=True))
    op.add_column("document_embeddings", sa.Column("element_type", sa.String(), nullable=True))
    op.add_column("document_embeddings", sa.Column("bounding_box", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("document_embeddings", "bounding_box")
    op.drop_column("document_embeddings", "element_type")
    op.drop_column("document_embeddings", "page_number")
