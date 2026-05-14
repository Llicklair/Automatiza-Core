"""Create verifactu_chain table — append-only registry per RD 1007/2023.

FAC.HASH — cadena hash encadenada por tenant (Reglamento Verifactu Art. 8):
cada registro contiene `huella` (SHA-256 del payload canónico de la factura
incluyendo `huella_anterior`). El primer registro del tenant tiene
`huella_anterior IS NULL`.

Append-only enforced en Postgres mediante triggers PL/pgSQL que rechazan
UPDATE y DELETE. En SQLite (tests) los triggers se omiten — la inmutabilidad
queda enforced solo por código.

Revision ID: 0011_verifactu_chain
Revises: 0010_invoice_counter   (la 0010 fue eliminada; este revises encadena
                                  directo a la última válida 0009)
"""

from alembic import op

revision = "0011_verifactu_chain"
down_revision = "0009_user_invitations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS verifactu_chain (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            invoice_id UUID NOT NULL,
            huella VARCHAR(64) NOT NULL,
            huella_anterior VARCHAR(64),
            payload_canonico TEXT NOT NULL,
            nif_emisor VARCHAR(20) NOT NULL,
            serie_factura VARCHAR(16) NOT NULL,
            numero_factura VARCHAR(100) NOT NULL,
            fecha_emision TIMESTAMP WITH TIME ZONE NOT NULL,
            importe_total NUMERIC(12, 2) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_verifactu_chain_tenant_created "
        "ON verifactu_chain(tenant_id, created_at)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_verifactu_chain_invoice "
        "ON verifactu_chain(invoice_id)"
    )

    # Triggers append-only (solo Postgres).
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION verifactu_chain_reject_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'verifactu_chain is append-only (RD 1007/2023)';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            DROP TRIGGER IF EXISTS verifactu_chain_no_update ON verifactu_chain;
            CREATE TRIGGER verifactu_chain_no_update
            BEFORE UPDATE ON verifactu_chain
            FOR EACH ROW EXECUTE FUNCTION verifactu_chain_reject_mutation();
            """
        )
        op.execute(
            """
            DROP TRIGGER IF EXISTS verifactu_chain_no_delete ON verifactu_chain;
            CREATE TRIGGER verifactu_chain_no_delete
            BEFORE DELETE ON verifactu_chain
            FOR EACH ROW EXECUTE FUNCTION verifactu_chain_reject_mutation();
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS verifactu_chain_no_update ON verifactu_chain")
        op.execute("DROP TRIGGER IF EXISTS verifactu_chain_no_delete ON verifactu_chain")
        op.execute("DROP FUNCTION IF EXISTS verifactu_chain_reject_mutation()")
    op.execute("DROP INDEX IF EXISTS ix_verifactu_chain_invoice")
    op.execute("DROP INDEX IF EXISTS ix_verifactu_chain_tenant_created")
    op.execute("DROP TABLE IF EXISTS verifactu_chain")
