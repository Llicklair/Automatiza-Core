"""Add is_backfilled flag and backfilled_at to verifactu_chain (A.5).

A.5 backfill histórico — para tenants que migran desde Holded/A3/CSV con
facturas anteriores a la activación de FAC.HASH, se reconstruye la cadena
hash retroactivamente preservando `fecha_emision` real. La columna
`is_backfilled` marca esas entradas para que el auditor pueda distinguir
los hashes calculados a posteriori de los firmados en tiempo real.

Append-only sigue siendo enforced por los triggers de 0011 — el backfill
inserta exclusivamente registros nuevos en orden cronológico una sola vez
por tenant.

Revision ID: 0018_verifactu_backfill_flag
Revises: 0017_backup_records
"""

from alembic import op

revision = "0018_verifactu_backfill_flag"
down_revision = "0017_backup_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Postgres soporta IF NOT EXISTS en ADD COLUMN; SQLite (tests) no.
    if dialect == "postgresql":
        op.execute(
            "ALTER TABLE verifactu_chain " "ADD COLUMN IF NOT EXISTS is_backfilled BOOLEAN NOT NULL DEFAULT FALSE"
        )
        op.execute("ALTER TABLE verifactu_chain " "ADD COLUMN IF NOT EXISTS backfilled_at TIMESTAMP WITH TIME ZONE")
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_verifactu_chain_backfilled "
            "ON verifactu_chain(tenant_id, is_backfilled) WHERE is_backfilled = TRUE"
        )
    else:
        # SQLite: añade columnas con default sin IF NOT EXISTS.
        op.execute("ALTER TABLE verifactu_chain ADD COLUMN is_backfilled BOOLEAN NOT NULL DEFAULT 0")
        op.execute("ALTER TABLE verifactu_chain ADD COLUMN backfilled_at TIMESTAMP")


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_verifactu_chain_backfilled")
        op.execute("ALTER TABLE verifactu_chain DROP COLUMN IF EXISTS backfilled_at")
        op.execute("ALTER TABLE verifactu_chain DROP COLUMN IF EXISTS is_backfilled")
    # SQLite no soporta DROP COLUMN antes de 3.35 — se omite en tests.
