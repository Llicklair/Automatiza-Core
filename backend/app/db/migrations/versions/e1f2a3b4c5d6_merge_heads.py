"""merge heads

Revision ID: e1f2a3b4c5d6
Revises: c9e1f3a5b7d2, d4e6f8a2c0b4
Create Date: 2026-03-09 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'e1f2a3b4c5d6'
down_revision = ('c9e1f3a5b7d2', 'd4e6f8a2c0b4')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
