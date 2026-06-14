"""SEC.RLS Fase B — rol de aplicación no-superusuario + policies simétricas.

La RLS (migración 0016) era INERTE porque el runtime conectaba como `pyme_user`,
el superusuario de bootstrap: un superusuario (o rol `BYPASSRLS`) ignora todas
las policies aunque la tabla esté `FORCE ROW LEVEL SECURITY`. Esta migración:

  1. Crea el rol de aplicación `pyme_app` (NOSUPERUSER NOBYPASSRLS) + grants. El
     runtime pasa a conectar con él (settings.DATABASE_URL); las migraciones
     siguen usando `pyme_user` (settings.ADMIN_DATABASE_URL).
  2. Normaliza las policies a `WITH CHECK` SIMÉTRICO con el `USING` (permisivo
     cuando no hay tenant en contexto), para no romper las escrituras de los
     flujos sin contexto (login, portal, webhooks, lecturas globales del
     scheduler) y a la vez bloquear escrituras cross-tenant cuando SÍ lo hay.

Lógica idéntica al bootstrap del desktop — fuente única en
`app.db.security_bootstrap`. Idempotente y Postgres-only.

Revision ID: 0060_app_role_rls
Revises: 0059_onboarding_llm_step
"""

from alembic import op
from sqlalchemy import text

from app.db.security_bootstrap import ensure_app_role, ensure_rls_policies

revision = "0060_app_role_rls"
down_revision = "0059_onboarding_llm_step"
branch_labels = None
depends_on = None

APP_ROLE = "pyme_app"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    # Normaliza las policies (0016/0025 tenían WITH CHECK estricto) y crea el rol.
    ensure_rls_policies(bind)
    ensure_app_role(bind)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    # Revoca privilegios y elimina el rol. Las policies se dejan tal cual (son
    # inocuas con el rol superusuario de vuelta, que las bypassa igualmente).
    bind.execute(
        text(
            f"""
            DO $$ BEGIN
              IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN
                EXECUTE 'REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {APP_ROLE}';
                EXECUTE 'REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {APP_ROLE}';
                EXECUTE 'REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM {APP_ROLE}';
                EXECUTE 'REVOKE USAGE ON SCHEMA public FROM {APP_ROLE}';
                EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
                        'REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM {APP_ROLE}';
                EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
                        'REVOKE USAGE, SELECT, UPDATE ON SEQUENCES FROM {APP_ROLE}';
                EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
                        'REVOKE EXECUTE ON FUNCTIONS FROM {APP_ROLE}';
                EXECUTE 'DROP ROLE {APP_ROLE}';
              END IF;
            END $$;
            """
        )
    )
