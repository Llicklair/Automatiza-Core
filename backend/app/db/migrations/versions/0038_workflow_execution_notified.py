"""Flag `notified` en workflow_executions para el alertado de fallos.

El sweep `check_failed_workflow_executions` marca esta columna tras avisar al
gestor de una ejecución fallida, para no notificar dos veces.

Revision ID: 0038_workflow_execution_notified
Revises: 0037_llm_usage_monthly
"""

import sqlalchemy as sa
from alembic import op

revision = "0038_workflow_execution_notified"
down_revision = "0037_llm_usage_monthly"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_executions",
        sa.Column(
            "notified",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("workflow_executions", "notified")
