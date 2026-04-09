"""add icon to ai_employees

Revision ID: e3d2c1b0a9f8
Revises: f9e8d7c6b5a4
Create Date: 2026-04-08
"""
from alembic import op
import sqlalchemy as sa

revision = "e3d2c1b0a9f8"
down_revision = "f9e8d7c6b5a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ai_employees", sa.Column("icon", sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_employees", "icon")
