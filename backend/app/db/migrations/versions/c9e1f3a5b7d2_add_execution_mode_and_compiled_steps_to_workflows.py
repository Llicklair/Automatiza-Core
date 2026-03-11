"""add_execution_mode_and_compiled_steps_to_workflows

Revision ID: c9e1f3a5b7d2
Revises: b1e3f8a2c9d0
Create Date: 2026-03-09 11:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c9e1f3a5b7d2'
down_revision: str | None = 'b1e3f8a2c9d0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'workflows',
        sa.Column(
            'execution_mode',
            sa.String(length=20),
            nullable=False,
            server_default='reasoning',
        )
    )
    op.add_column(
        'workflows',
        sa.Column(
            'compiled_steps',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        )
    )


def downgrade() -> None:
    op.drop_column('workflows', 'compiled_steps')
    op.drop_column('workflows', 'execution_mode')
