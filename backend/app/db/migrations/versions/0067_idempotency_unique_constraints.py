"""UNIQUE de idempotencia: nóminas y integraciones (anti doble-insert).

Cierra dos bugs de doble-inserción que tenían un guard *check-then-act* (TOCTOU)
en la aplicación pero NINGUNA barrera en BD, de modo que dos ejecuciones
concurrentes los saltaban:

- `payrolls`: `generate_all_payrolls` pre-cargaba los empleados con nómina y los
  saltaba, pero dos batches a la vez duplicaban (se vieron 120 filas para 5
  empleados). El handler `except IntegrityError` ya existía en el código,
  esperando esta UNIQUE. Una nómina por (tenant, empleado, period_start).
- `tenant_integrations`: `connect_telegram`/otros hacían select-then-add; dos
  conexiones concurrentes creaban integraciones duplicadas. Una por (tenant, tipo).

Antes de crear cada constraint se DEDUPLICAN las filas existentes (idempotente):
se conserva la "mejor" de cada grupo y se borran las demás. En `payrolls` la mejor
es la de mayor estado (paid > approved > draft) y, a igualdad, la más reciente.
En `tenant_integrations`, la más reciente.

Revision ID: 0067_idempotency_unique_constraints
Revises: 0066_demo_data_flag
"""

from alembic import op

revision = "0067_idempotency_unique_constraints"
down_revision = "0066_demo_data_flag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── tenant_integrations: dedup (conserva la más reciente) + UNIQUE ──────────
    op.execute(
        """
        DELETE FROM tenant_integrations
        WHERE id IN (
            SELECT id FROM (
                SELECT id, row_number() OVER (
                    PARTITION BY tenant_id, integration_type
                    ORDER BY created_at DESC, id DESC
                ) AS rn
                FROM tenant_integrations
            ) t WHERE t.rn > 1
        )
        """
    )
    op.create_unique_constraint(
        "uq_tenant_integration_type",
        "tenant_integrations",
        ["tenant_id", "integration_type"],
    )

    # ── payrolls: dedup (conserva paid>approved>draft, luego la más reciente) ───
    op.execute(
        """
        DELETE FROM payrolls
        WHERE id IN (
            SELECT id FROM (
                SELECT id, row_number() OVER (
                    PARTITION BY tenant_id, employee_id, period_start
                    ORDER BY
                        CASE status WHEN 'paid' THEN 3 WHEN 'approved' THEN 2 ELSE 1 END DESC,
                        created_at DESC, id DESC
                ) AS rn
                FROM payrolls
            ) t WHERE t.rn > 1
        )
        """
    )
    op.create_unique_constraint(
        "uq_payroll_tenant_emp_period",
        "payrolls",
        ["tenant_id", "employee_id", "period_start"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_payroll_tenant_emp_period", "payrolls", type_="unique")
    op.drop_constraint("uq_tenant_integration_type", "tenant_integrations", type_="unique")
