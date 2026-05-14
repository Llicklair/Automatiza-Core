"""SEC.RLS — Row-Level Security en Postgres con `app.current_tenant`.

Activa RLS en todas las tablas con columna `tenant_id` y crea una política
genérica que filtra por la variable de sesión `app.current_tenant`. El
backend FastAPI setea esa variable tras autenticar al usuario, mediante
`SET LOCAL app.current_tenant = '<uuid>'` al inicio de cada transacción.

Consensuado en Ronda 7 §25.1 — la barrera RLS de Postgres es la única defensa
fuerte contra el caso "agente con bug pasa el tenant_id equivocado por error
del prompt". Hasta esta migración la única barrera vivía en código.

En SQLite (tests) las policies no se aplican — RLS es Postgres-only.

Revision ID: 0016_sec_rls
Revises: 0015_metering
"""

from alembic import op


revision = "0016_sec_rls"
down_revision = "0015_metering"
branch_labels = None
depends_on = None


# Nombre de la política. Único por tabla para evitar colisiones futuras.
POLICY_NAME = "rls_tenant_isolation"


def _enable_rls_sql(table: str) -> str:
    return f"""
        ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
        ALTER TABLE {table} FORCE ROW LEVEL SECURITY;

        DROP POLICY IF EXISTS {POLICY_NAME} ON {table};
        CREATE POLICY {POLICY_NAME} ON {table}
            USING (
                tenant_id::text = current_setting('app.current_tenant', true)
                OR current_setting('app.current_tenant', true) IS NULL
                OR current_setting('app.current_tenant', true) = ''
            )
            WITH CHECK (
                tenant_id::text = current_setting('app.current_tenant', true)
            );
    """


def _disable_rls_sql(table: str) -> str:
    return f"""
        DROP POLICY IF EXISTS {POLICY_NAME} ON {table};
        ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
    """


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Detectar dinámicamente todas las tablas con columna `tenant_id` para no
    # mantener una lista que se queda atrás cuando se añaden tablas nuevas.
    rows = bind.execute(
        """
        SELECT DISTINCT table_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND column_name = 'tenant_id'
          AND data_type IN ('uuid', 'character varying', 'text');
        """
    ).fetchall()

    tables = sorted({row[0] for row in rows})
    for table in tables:
        op.execute(_enable_rls_sql(table))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    rows = bind.execute(
        """
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public'
        """
    ).fetchall()
    for row in rows:
        op.execute(f"DROP POLICY IF EXISTS {POLICY_NAME} ON {row[0]}")
        op.execute(f"ALTER TABLE {row[0]} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {row[0]} DISABLE ROW LEVEL SECURITY")
