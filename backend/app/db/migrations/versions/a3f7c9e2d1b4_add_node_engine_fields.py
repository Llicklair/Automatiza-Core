"""Add node engine fields to workflow_executions and pending_approvals

Revision ID: a3f7c9e2d1b4
Revises: 232fec5cbb97
Create Date: 2026-03-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a3f7c9e2d1b4'
down_revision: Union[str, None] = '232fec5cbb97'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # WorkflowExecution: node engine fields
    op.add_column('workflow_executions', sa.Column('node_states', postgresql.JSONB(), nullable=True, server_default='{}'))
    op.add_column('workflow_executions', sa.Column('current_node_id', sa.String(100), nullable=True))
    op.add_column('workflow_executions', sa.Column('paused_at', sa.DateTime(timezone=True), nullable=True))

    # PendingApproval: link to workflow execution
    op.add_column('pending_approvals', sa.Column('execution_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_pending_approvals_execution_id',
        'pending_approvals', 'workflow_executions',
        ['execution_id'], ['id'],
    )
    op.create_index('ix_pending_approvals_execution_id', 'pending_approvals', ['execution_id'])


def downgrade() -> None:
    op.drop_index('ix_pending_approvals_execution_id', table_name='pending_approvals')
    op.drop_constraint('fk_pending_approvals_execution_id', 'pending_approvals', type_='foreignkey')
    op.drop_column('pending_approvals', 'execution_id')

    op.drop_column('workflow_executions', 'paused_at')
    op.drop_column('workflow_executions', 'current_node_id')
    op.drop_column('workflow_executions', 'node_states')
