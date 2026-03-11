"""add_holded_id_to_clients

Revision ID: a1b2c3d4e5f6
Revises: (85d22b01f159, a6bf183c8e0c)
Create Date: 2026-02-26 09:38:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
# Merge de las dos ramas paralelas: embeddings y category
revision: str = 'a1b2c3d4e5f6'
down_revision: str | tuple[str, ...] = ('85d22b01f159', 'a6bf183c8e0c')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'clients',
        sa.Column('holded_id', sa.String(length=255), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('clients', 'holded_id')
