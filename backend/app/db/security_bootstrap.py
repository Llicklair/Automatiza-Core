"""SEC.RLS — objetos de seguridad idempotentes (rol de app + policies RLS).

Fuente ÚNICA de verdad para los dos objetos que hacen que la Row-Level Security
de Postgres se aplique de verdad:

1. **Rol de aplicación `pyme_app`** (`NOSUPERUSER NOBYPASSRLS`). El runtime DEBE
   conectar con este rol: un superusuario (o un rol `BYPASSRLS`) ignora TODAS las
   policies aunque la tabla esté `FORCE ROW LEVEL SECURITY`. Conectar como
   `pyme_user` (el bootstrap superuser) dejaba la RLS completamente inerte.

2. **Policies RLS** por tabla con columna `tenant_id`, con `USING` y `WITH CHECK`
   SIMÉTRICOS y **fail-closed** (SEC.RLS Fase C):
       (tenant_id = app.current_tenant) OR app.rls_bypass = 'on'
   → Con tenant fijado (agente/tool/HTTP/worker): lecturas y escrituras quedan
     ancladas a ese tenant; un intento cross-tenant se bloquea (el threat model
     real: "agente con bug o prompt-injection pasa el tenant_id equivocado").
   → Sin tenant fijado y sin bypass: **CERO filas** (fail-closed). Un path que
     llegue a Postgres sin fijar tenant ya NO filtra datos de otros tenants;
     falla cerrado (se rompe de forma visible) en vez de abrir.
   → Los cuatro flujos legítimos sin tenant (auth pre-tenant, portal de cliente,
     webhooks externos, SELECT inicial cross-tenant del scheduler) activan
     `app.rls_bypass = 'on'` vía el context manager `rls_bypass()`
     (`app.core.tenant_context`), que el listener de `app.db.rls` espeja al GUC.

Idempotente y Postgres-only. Recibe una `Connection` síncrona de SQLAlchemy y se
ejecuta SIEMPRE como rol administrador (`pyme_user`). Lo invocan:
  - La migración alembic `0060_app_role_rls` (despliegues incrementales).
  - El bootstrap del desktop (`_desktop_migrate.py`), que en BD nueva hace
    `create_all` + `stamp head` y SE SALTA los `upgrade()` de las migraciones —
    sin este paso, una instalación nueva quedaría sin RLS ni rol de app.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection

APP_ROLE = "pyme_app"
POLICY_NAME = "rls_tenant_isolation"
_DML = "SELECT, INSERT, UPDATE, DELETE"


def ensure_app_role(connection: Connection, app_password: str = "pyme_pass") -> None:
    """Crea (idempotente) el rol de aplicación no-privilegiado y sus grants.

    Incluye `ALTER DEFAULT PRIVILEGES` para que las tablas/secuencias FUTURAS
    creadas por el admin queden accesibles sin re-granting manual.
    """
    if connection.dialect.name != "postgresql":
        return

    connection.execute(
        text(
            f"""
            DO $$ BEGIN
              IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN
                CREATE ROLE {APP_ROLE} LOGIN NOSUPERUSER NOBYPASSRLS
                  NOCREATEDB NOCREATEROLE PASSWORD '{app_password}';
              END IF;
            END $$;
            """
        )
    )
    connection.execute(text(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE};"))
    connection.execute(text(f"GRANT {_DML} ON ALL TABLES IN SCHEMA public TO {APP_ROLE};"))
    connection.execute(text(f"GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO {APP_ROLE};"))
    connection.execute(text(f"GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO {APP_ROLE};"))
    # Privilegios por defecto para objetos FUTUROS (creados por el rol admin actual).
    connection.execute(text(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT {_DML} ON TABLES TO {APP_ROLE};"))
    connection.execute(
        text("ALTER DEFAULT PRIVILEGES IN SCHEMA public " f"GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {APP_ROLE};")
    )
    connection.execute(text(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO {APP_ROLE};"))


def ensure_rls_policies(connection: Connection) -> None:
    """Activa RLS (`ENABLE` + `FORCE`) y (re)crea la policy simétrica en toda
    tabla con columna `tenant_id`. Idempotente (DROP POLICY IF EXISTS + CREATE).

    Detecta las tablas dinámicamente para no mantener una lista que se queda
    atrás al añadir tablas nuevas. Normaliza también policies antiguas con
    `WITH CHECK` estricto (migraciones 0016 / 0025) a la forma simétrica.
    """
    if connection.dialect.name != "postgresql":
        return

    rows = connection.execute(
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
        connection.execute(text(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY;'))
        connection.execute(text(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY;'))
        connection.execute(text(f'DROP POLICY IF EXISTS {POLICY_NAME} ON "{table}";'))
        connection.execute(
            text(
                f"""
                CREATE POLICY {POLICY_NAME} ON "{table}"
                    USING (
                        tenant_id::text = current_setting('app.current_tenant', true)
                        OR current_setting('app.rls_bypass', true) = 'on'
                    )
                    WITH CHECK (
                        tenant_id::text = current_setting('app.current_tenant', true)
                        OR current_setting('app.rls_bypass', true) = 'on'
                    );
                """
            )
        )


def ensure_security_objects(connection: Connection, app_password: str = "pyme_pass") -> None:
    """Garantiza policies RLS + rol de aplicación. Punto de entrada del bootstrap
    desktop (cubre BD nuevas que se saltan los `upgrade()` de las migraciones)."""
    ensure_rls_policies(connection)
    ensure_app_role(connection, app_password)
