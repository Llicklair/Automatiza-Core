"""Add payroll SS breakdown fields and employee irpf_rate

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-03-12
"""
import sqlalchemy as sa
from alembic import op

revision = "a7b8c9d0e1f2"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Employee: IRPF rate configurable
    # op.add_column("employees", sa.Column("irpf_rate", sa.Numeric(5, 2), server_default="15.00", nullable=True))

    # Payroll: SS breakdown
    op.add_column("payrolls", sa.Column("ss_contingencias_comunes", sa.Numeric(10, 2), server_default="0", nullable=True))
    op.add_column("payrolls", sa.Column("ss_desempleo", sa.Numeric(10, 2), server_default="0", nullable=True))
    op.add_column("payrolls", sa.Column("ss_formacion_profesional", sa.Numeric(10, 2), server_default="0", nullable=True))
    op.add_column("payrolls", sa.Column("ss_mei", sa.Numeric(10, 2), server_default="0", nullable=True))
    op.add_column("payrolls", sa.Column("irpf", sa.Numeric(10, 2), server_default="0", nullable=True))
    op.add_column("payrolls", sa.Column("other_deductions", sa.Numeric(10, 2), server_default="0", nullable=True))


def downgrade() -> None:
    op.drop_column("payrolls", "other_deductions")
    op.drop_column("payrolls", "irpf")
    op.drop_column("payrolls", "ss_mei")
    op.drop_column("payrolls", "ss_formacion_profesional")
    op.drop_column("payrolls", "ss_desempleo")
    op.drop_column("payrolls", "ss_contingencias_comunes")
    op.drop_column("employees", "irpf_rate")
