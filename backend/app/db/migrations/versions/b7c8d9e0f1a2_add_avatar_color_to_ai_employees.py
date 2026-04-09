"""add avatar_color to ai_employees

Revision ID: b7c8d9e0f1a2
Revises: e3d2c1b0a9f8
Create Date: 2026-04-08
"""
from alembic import op
import sqlalchemy as sa

revision = "b7c8d9e0f1a2"
down_revision = "e3d2c1b0a9f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ai_employees", sa.Column("avatar_color", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_employees", "avatar_color")
