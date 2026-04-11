"""add email to employees

Revision ID: a1b2c3d4e5f7
Revises: z9y8x7w6v5u4
Create Date: 2026-03-20

"""

import sqlalchemy as sa
from alembic import op

revision = "a1b2c3d4e5f7"
down_revision = "z9y8x7w6v5u4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("email", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("employees", "email")
