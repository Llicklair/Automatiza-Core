"""Columna `cuota_solidaridad` en payrolls (parte trabajador).

Cotización adicional de solidaridad (RD-ley 2/2023, vigente desde 2025) sobre el
salario que excede la base máxima de cotización. Aquí se persiste la parte a
cargo del trabajador para poder itemizarla en la nómina. Las nóminas anteriores
se backfillean a 0 (no tenían este concepto calculado).

Revision ID: 0039_payroll_cuota_solidaridad
Revises: 0038_workflow_execution_notified
"""

import sqlalchemy as sa
from alembic import op

revision = "0039_payroll_cuota_solidaridad"
down_revision = "0038_workflow_execution_notified"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payrolls",
        sa.Column(
            "cuota_solidaridad",
            sa.Numeric(10, 2),
            nullable=True,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("payrolls", "cuota_solidaridad")
