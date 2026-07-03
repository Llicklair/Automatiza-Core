"""Drop the regulated VeriFactu/SIF core.

El ERP deja de emitir facturas fiscales y de ser un SIF: se elimina por
completo la cadena VeriFactu (RD 1007/2023). Esta migración destruye el
esquema SIF creado por 0011/0018/0023:

* Triggers + función append-only de 0011 sobre `verifactu_chain`.
* Tabla `verifactu_chain` (registro encadenado por huella).
* Tabla `verifactu_config` (modo de remisión por tenant).
* Columnas `invoices.verifactu_status` y `invoices.verifactu_sent_at`.

Las facturas creadas por el ERP pasan a ser PROFORMAS sin valor fiscal, así
que no hay dato fiscal que preservar. No se editan las migraciones históricas
(0011/0012/0018/0023): la historia sigue lineal.

Revision ID: 0072_drop_verifactu_sif
Revises: 0071_invoice_rectifies_once
"""

import sqlalchemy as sa
from alembic import op

revision = "0072_drop_verifactu_sif"
down_revision = "0071_invoice_rectifies_once"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    # 1) Triggers + función append-only de 0011 (solo Postgres). Se sueltan ANTES
    #    que la función (que depende de ellos) y que la tabla.
    if is_pg:
        op.execute("DROP TRIGGER IF EXISTS verifactu_chain_no_update ON verifactu_chain")
        op.execute("DROP TRIGGER IF EXISTS verifactu_chain_no_delete ON verifactu_chain")
        op.execute("DROP FUNCTION IF EXISTS verifactu_chain_reject_mutation()")

    # 2) Tablas del núcleo SIF.
    op.execute("DROP TABLE IF EXISTS verifactu_config")
    op.execute("DROP TABLE IF EXISTS verifactu_chain")

    # 3) Columnas VeriFactu de invoices (nunca creadas por migración previa, de
    #    ahí el IF EXISTS: no-op si el esquema se construyó vía migraciones).
    if is_pg:
        op.execute("ALTER TABLE invoices DROP COLUMN IF EXISTS verifactu_status")
        op.execute("ALTER TABLE invoices DROP COLUMN IF EXISTS verifactu_sent_at")
    else:
        existing = {c["name"] for c in sa.inspect(bind).get_columns("invoices")}
        to_drop = [c for c in ("verifactu_status", "verifactu_sent_at") if c in existing]
        if to_drop:
            with op.batch_alter_table("invoices") as batch:
                for col in to_drop:
                    batch.drop_column(col)


def downgrade() -> None:
    """Recrea el esquema SIF (schema-only, sin triggers ni datos) para mantener
    la historia lineal reversible. No repuebla la cadena ni el modo de remisión.
    """
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    if is_pg:
        op.execute("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS verifactu_status VARCHAR(30)")
        op.execute("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS verifactu_sent_at TIMESTAMP WITH TIME ZONE")
    else:
        with op.batch_alter_table("invoices") as batch:
            batch.add_column(sa.Column("verifactu_status", sa.String(length=30), nullable=True))
            batch.add_column(sa.Column("verifactu_sent_at", sa.DateTime(timezone=True), nullable=True))

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
            is_backfilled BOOLEAN NOT NULL DEFAULT FALSE,
            backfilled_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_verifactu_chain_invoice ON verifactu_chain(invoice_id)")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS verifactu_config (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL UNIQUE,
            mode VARCHAR(32) NOT NULL DEFAULT 'no_remission',
            updated_by UUID,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """
    )
