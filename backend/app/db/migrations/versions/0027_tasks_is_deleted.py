"""Soft-delete en tasks — bug cleanup vs WORM audit_log (lessons 2026-05-19).

El endpoint DELETE /api/v1/tasks/cleanup hacía DELETE FROM audit_log y
DELETE FROM tasks. El trigger audit_log_no_delete (mig 0012) bloquea el primer
DELETE; el segundo además rompía FK desde audit_log → tasks. Resultado:
la operación dejaba el request colgado y la UI con "Limpiar(N)" eterno.

Solución: marcar tasks como `is_deleted=true` en lugar de borrarlas. Los
audit_log entries quedan intactos (WORM compliance). Las queries de listado
filtran `is_deleted=false`.

Revision ID: 0027_tasks_is_deleted
Revises: 0026_product_location
"""

import sqlalchemy as sa
from alembic import op

revision = "0027_tasks_is_deleted"
down_revision = "0026_product_location"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index(
        "ix_tasks_is_deleted",
        "tasks",
        ["tenant_id", "is_deleted"],
    )


def downgrade() -> None:
    op.drop_index("ix_tasks_is_deleted", table_name="tasks")
    op.drop_column("tasks", "is_deleted")
