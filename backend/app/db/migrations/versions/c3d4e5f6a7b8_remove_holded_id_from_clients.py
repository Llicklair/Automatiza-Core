"""Remove holded_id from clients

Revision ID: c3d4e5f6a7b8
Revises: m3r6g2024odl
Create Date: 2026-03-21

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "m3r6g2024odl"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("clients", "holded_id")


def downgrade() -> None:
    op.add_column("clients", sa.Column("holded_id", sa.String(length=255), nullable=True))
