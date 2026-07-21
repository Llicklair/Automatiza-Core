"""Triggers append-only (WORM) para sif_events — misma protección que la
cadena de facturación (0011). Sin ellos la inalterabilidad de los eventos era
solo detectiva (verify_events_integrity), no preventiva a nivel de BD.

Solo Postgres; en SQLite (tests) la inmutabilidad es a nivel de código.

Revision ID: 0076_sif_events_worm
Revises: 0075_invoice_substitutes
"""

from alembic import op

revision = "0076_sif_events_worm"
down_revision = "0075_invoice_substitutes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(
        """
        CREATE OR REPLACE FUNCTION sif_events_reject_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'sif_events is append-only (RD 1007/2023 Art. 14)';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS sif_events_no_update ON sif_events;
        CREATE TRIGGER sif_events_no_update
        BEFORE UPDATE ON sif_events
        FOR EACH ROW EXECUTE FUNCTION sif_events_reject_mutation();
        """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS sif_events_no_delete ON sif_events;
        CREATE TRIGGER sif_events_no_delete
        BEFORE DELETE ON sif_events
        FOR EACH ROW EXECUTE FUNCTION sif_events_reject_mutation();
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("DROP TRIGGER IF EXISTS sif_events_no_update ON sif_events")
    op.execute("DROP TRIGGER IF EXISTS sif_events_no_delete ON sif_events")
    op.execute("DROP FUNCTION IF EXISTS sif_events_reject_mutation()")
