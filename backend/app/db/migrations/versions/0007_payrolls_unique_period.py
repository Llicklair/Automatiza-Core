"""Unique payroll per (tenant, employee, period_start).

Antes de esta migración la tabla `payrolls` solo tenía PK en `id` —
nada impedía generar la nómina del mismo empleado y mismo mes N veces.
Las tools `calculate_and_create_payroll` y `generate_all_payrolls` no
verificaban en código y la BD tampoco bloqueaba — sesión tras sesión
se acumulaban duplicados (vimos 136 filas para el mismo set de 5
empleados, ~115 duplicados).

Este UNIQUE INDEX cierra la puerta a nivel BD: no es posible que un
empleado tenga dos nóminas para el mismo period_start dentro del mismo
tenant. Basado en `period_start` (no en mes+año explícitos) porque ese
es el campo que las tools usan al insertar.

NOTA: las tools deben normalizar period_start al primer día del mes
00:00 UTC (la migración previa de cleanup ya normalizó las filas
existentes).

Revision ID: 0007_payroll_unique
Revises: 0006_emp_unique_nif
"""

from alembic import op

revision = "0007_payroll_unique"
down_revision = "0006_emp_unique_nif"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS payrolls_unique_per_period
        ON payrolls (tenant_id, employee_id, period_start)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS payrolls_unique_per_period")
