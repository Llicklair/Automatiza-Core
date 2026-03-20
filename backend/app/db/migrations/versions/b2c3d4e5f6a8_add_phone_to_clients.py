"""add phone to clients

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
Create Date: 2026-03-20

"""
from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a8"
down_revision = "a1b2c3d4e5f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("phone", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("clients", "phone")
