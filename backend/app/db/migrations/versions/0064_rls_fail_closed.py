"""SEC.RLS Fase C — endurece la RLS de fail-OPEN a fail-CLOSED.

Hasta aquí (migración 0060) la policy era permisiva cuando no había tenant en
contexto: `app.current_tenant IS NULL OR = ''` dejaba pasar TODAS las filas. Un
solo path que llegara a Postgres sin fijar tenant (bug, job, olvido) filtraba
datos de todos los tenants en silencio.

Esta migración reescribe la policy a fail-closed: sin tenant y sin bypass
explícito → CERO filas. Los cuatro flujos legítimos sin tenant (auth pre-tenant,
portal de cliente, webhooks, SELECT cross-tenant del scheduler) activan
`app.rls_bypass = 'on'` vía el context manager `rls_bypass()`.

La lógica vive en `app.db.security_bootstrap.ensure_rls_policies` (fuente única,
idempotente), así que esta migración simplemente la re-ejecuta. Postgres-only.

Revision ID: 0064_rls_fail_closed
Revises: 0063_drop_social_account_tokens
"""

from alembic import op

from app.db.security_bootstrap import ensure_rls_policies

revision = "0064_rls_fail_closed"
down_revision = "0063_drop_social_account_tokens"
branch_labels = None
depends_on = None

POLICY_NAME = "rls_tenant_isolation"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    # Re-(crea) la policy en su forma fail-closed actual (DROP IF EXISTS + CREATE).
    ensure_rls_policies(bind)


def downgrade() -> None:
    """Revierte a la policy permisiva (fail-open) de la Fase B."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    from sqlalchemy import text

    rows = bind.execute(
        text(
            """
            SELECT DISTINCT table_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND column_name = 'tenant_id'
              AND data_type IN ('uuid', 'character varying', 'text');
            """
        )
    ).fetchall()

    for (table,) in sorted(rows):
        op.execute(f'DROP POLICY IF EXISTS {POLICY_NAME} ON "{table}";')
        op.execute(
            f"""
            CREATE POLICY {POLICY_NAME} ON "{table}"
                USING (
                    tenant_id::text = current_setting('app.current_tenant', true)
                    OR current_setting('app.current_tenant', true) IS NULL
                    OR current_setting('app.current_tenant', true) = ''
                )
                WITH CHECK (
                    tenant_id::text = current_setting('app.current_tenant', true)
                    OR current_setting('app.current_tenant', true) IS NULL
                    OR current_setting('app.current_tenant', true) = ''
                );
            """
        )
