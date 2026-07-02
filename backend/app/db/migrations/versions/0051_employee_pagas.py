"""HR: employees.num_pagas y prorratear_pagas (pagas extra 12/14).

Revision ID: 0051_employee_pagas
Revises: 0050_post_retry_count
"""

from alembic import op

revision = "0051_employee_pagas"
down_revision = "0050_post_retry_count"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS num_pagas INTEGER DEFAULT 12")
    op.execute("ALTER TABLE employees " "ADD COLUMN IF NOT EXISTS prorratear_pagas BOOLEAN DEFAULT FALSE")


def downgrade() -> None:
    op.execute("ALTER TABLE employees DROP COLUMN IF EXISTS prorratear_pagas")
    op.execute("ALTER TABLE employees DROP COLUMN IF EXISTS num_pagas")
