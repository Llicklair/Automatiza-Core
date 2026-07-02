"""BAK.LOC + BAK.VF — Tabla de registro de backups locales del cliente.

El dump físico lo realiza `desktop/postgres-manager.js` con `pg_dump` nativo
(Postgres portable) hacia la ruta configurada en `BackupStore` (DIS.IFACE).
Este registro persiste **metadatos** del backup (tamaño, hash SHA-256,
ruta, tipo full/verifactu) para alimentar el banner BAK.UI y permitir
auditoría posterior.

Append-only en Postgres (triggers) — un backup que ya se hizo no debe
poder retocarse para falsificar la fecha o el hash.

Revision ID: 0017_backup_records
Revises: 0016_sec_rls
"""

from alembic import op

revision = "0017_backup_records"
down_revision = "0016_sec_rls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS backup_record (
            id BIGSERIAL PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            kind VARCHAR(20) NOT NULL,
            destination_path VARCHAR(1000) NOT NULL,
            size_bytes BIGINT NOT NULL,
            sha256_hex VARCHAR(64) NOT NULL,
            encryption_key_label VARCHAR(50) NOT NULL,
            note TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_backup_record_tenant_created " "ON backup_record(tenant_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_backup_record_tenant_kind_created "
        "ON backup_record(tenant_id, kind, created_at DESC)"
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Reutiliza la función `sec_worm_reject_mutation` creada en 0012.
        op.execute("DROP TRIGGER IF EXISTS backup_record_no_update ON backup_record")
        op.execute(
            """
            CREATE TRIGGER backup_record_no_update
            BEFORE UPDATE ON backup_record
            FOR EACH ROW EXECUTE FUNCTION sec_worm_reject_mutation();
            """
        )
        op.execute("DROP TRIGGER IF EXISTS backup_record_no_delete ON backup_record")
        op.execute(
            """
            CREATE TRIGGER backup_record_no_delete
            BEFORE DELETE ON backup_record
            FOR EACH ROW EXECUTE FUNCTION sec_worm_reject_mutation();
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS backup_record_no_update ON backup_record")
        op.execute("DROP TRIGGER IF EXISTS backup_record_no_delete ON backup_record")
    op.execute("DROP INDEX IF EXISTS ix_backup_record_tenant_kind_created")
    op.execute("DROP INDEX IF EXISTS ix_backup_record_tenant_created")
    op.execute("DROP TABLE IF EXISTS backup_record")
