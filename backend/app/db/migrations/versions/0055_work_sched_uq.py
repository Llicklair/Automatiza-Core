"""Constraint única (employee_id, day_of_week) en work_schedules.

Requerida por el ON CONFLICT del upsert de horarios — sin ella el endpoint
POST /hr/schedules/{employee_id} falla en Postgres. Antes de crearla se
eliminan posibles duplicados conservando la fila más reciente.
"""

from alembic import op

revision = "0055_work_sched_uq"
down_revision = "0054_client_mkt_consent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM work_schedules a
        USING work_schedules b
        WHERE a.employee_id = b.employee_id
          AND a.day_of_week = b.day_of_week
          AND a.id < b.id
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_work_schedule_emp_day'
            ) THEN
                ALTER TABLE work_schedules
                    ADD CONSTRAINT uq_work_schedule_emp_day
                    UNIQUE (employee_id, day_of_week);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE work_schedules DROP CONSTRAINT IF EXISTS uq_work_schedule_emp_day"
    )
