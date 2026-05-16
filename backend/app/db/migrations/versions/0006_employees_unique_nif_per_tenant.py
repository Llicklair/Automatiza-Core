"""Unique NIF per tenant for employees (case-insensitive).

Antes de esta migración la tabla `employees` solo tenía PK en `id` —
nada impedía crear dos empleados con el mismo NIF dentro del mismo
tenant. La tool `create_employee` validaba en código pero con query
case-sensitive, lo que dejaba escapar duplicados con `12345678z` vs
`12345678Z` (el insert subía a uppercase, el query no).

Este partial UNIQUE INDEX cierra la puerta a nivel BD: dos empleados
con el mismo NIF (ignorando case) dentro de un mismo tenant son
imposibles. Permite NIF NULL por si en el futuro se admiten registros
sin NIF (e.g. extranjeros sin NIE temporalmente).

Revision ID: 0006_emp_unique_nif
Revises: 0005_pdf_text_report_skill
"""

from alembic import op

revision = "0006_emp_unique_nif"
down_revision = "0005_pdf_text_report_skill"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS employees_unique_nif_per_tenant
        ON employees (tenant_id, UPPER(nif))
        WHERE nif IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS employees_unique_nif_per_tenant")
