"""add doc_folder to ai_employees

Revision ID: f9e8d7c6b5a4
Revises: g1e2n3e4r5a6
Create Date: 2026-04-08
"""
import sqlalchemy as sa
from alembic import op

revision = "f9e8d7c6b5a4"
down_revision = "g1e2n3e4r5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ai_employees", sa.Column("doc_folder", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_employees", "doc_folder")
