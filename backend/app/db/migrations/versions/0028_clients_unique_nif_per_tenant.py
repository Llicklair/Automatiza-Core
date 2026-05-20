"""UNIQUE(tenant_id, nif) en clients — cerrar race en upsert de billing.

El flujo `agents/billing/_invoice_create_async.py:create_or_get_client`
hace SELECT por (tenant_id, nif) seguido de INSERT si no existe. Sin
constraint UNIQUE en BD, dos POST simultáneos del mismo cliente nuevo
(o bugs del flujo) crean duplicados que rompen reports (Modelo 347
agrega por NIF), conciliación bancaria y métricas.

La defensa correcta es server-side: UNIQUE INDEX con filtro
`nif IS NOT NULL AND nif <> ''` (los clientes sin NIF — particulares
ocasionales — se permiten múltiples).

**Importante**: si existen duplicados pre-existentes, la migración falla
con error claro listando los primeros 5. En ese caso, ejecutar manualmente
una limpieza antes de re-aplicar:

    SELECT tenant_id, nif, COUNT(*) FROM clients
     WHERE nif IS NOT NULL AND nif <> ''
     GROUP BY tenant_id, nif HAVING COUNT(*) > 1;

Revision ID: 0028_clients_unique_nif
Revises: 0027_tasks_is_deleted
"""

import sqlalchemy as sa
from alembic import op

revision = "0028_clients_unique_nif"
down_revision = "0027_tasks_is_deleted"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # Chequeo defensivo: si hay duplicados, parar antes de que falle el índice.
    # En SQLite (tests) la tabla puede estar vacía, así que el query devuelve [].
    dups = bind.execute(
        sa.text(
            "SELECT tenant_id, nif, COUNT(*) AS n FROM clients "
            "WHERE nif IS NOT NULL AND nif <> '' "
            "GROUP BY tenant_id, nif HAVING COUNT(*) > 1 LIMIT 5"
        )
    ).fetchall()
    if dups:
        preview = ", ".join(f"(tenant={r[0]}, nif={r[1]}, n={r[2]})" for r in dups)
        raise RuntimeError(
            "No se puede crear UNIQUE(tenant_id, nif) — hay duplicados existentes. "
            f"Primeros 5: {preview}. Mergear o borrar antes de re-aplicar."
        )

    # Partial UNIQUE index: solo aplica cuando nif está presente.
    # Postgres soporta WHERE clauses en índices; SQLite también desde 3.8.
    if bind.dialect.name == "postgresql":
        op.execute(
            "CREATE UNIQUE INDEX clients_unique_nif_per_tenant "
            "ON clients (tenant_id, nif) "
            "WHERE nif IS NOT NULL AND nif <> ''"
        )
    else:
        # SQLite (tests)
        op.execute(
            "CREATE UNIQUE INDEX clients_unique_nif_per_tenant "
            "ON clients (tenant_id, nif) "
            "WHERE nif IS NOT NULL AND nif != ''"
        )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS clients_unique_nif_per_tenant")
