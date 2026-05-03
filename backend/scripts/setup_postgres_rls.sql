-- Setup Postgres para RLS multi-tenant.
--
-- Crea dos roles:
--   pyme_user:  superusuario del proyecto (owner de las tablas, ejecuta
--               migraciones Alembic, hace queries de sistema/scheduler).
--   pyme_app:   rol sin BYPASSRLS que usa la app real. RLS aplica.
--
-- Uso:
--   psql -h localhost -p 5433 -U postgres -d postgres -f setup_postgres_rls.sql
--
-- Pre-requisito: que ya existan las bases pyme_db y pyme_db_test, owned by pyme_user.
-- (CREATE DATABASE pyme_db OWNER pyme_user;)

-- 1. Roles ─────────────────────────────────────────────────────────────────
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pyme_user') THEN
        CREATE USER pyme_user WITH PASSWORD 'pyme_pass' CREATEDB;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pyme_app') THEN
        CREATE USER pyme_app WITH PASSWORD 'pyme_app_pass';
    END IF;
END
$$;

-- 2. Grants en cada base de datos ──────────────────────────────────────────
-- Conéctate a cada BD (pyme_db, pyme_db_test) y ejecuta:
\c pyme_db

GRANT USAGE ON SCHEMA public TO pyme_app;
GRANT SELECT, INSERT, UPDATE, DELETE, REFERENCES ON ALL TABLES IN SCHEMA public TO pyme_app;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO pyme_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE, REFERENCES ON TABLES TO pyme_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO pyme_app;

\c pyme_db_test

GRANT USAGE ON SCHEMA public TO pyme_app;
GRANT SELECT, INSERT, UPDATE, DELETE, REFERENCES ON ALL TABLES IN SCHEMA public TO pyme_app;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO pyme_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE, REFERENCES ON TABLES TO pyme_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO pyme_app;

-- 3. Verificación ──────────────────────────────────────────────────────────
\c pyme_db
\du pyme_app

-- 4. Configuración de la app ───────────────────────────────────────────────
-- En .env del backend:
--
--   DATABASE_URL=postgresql+asyncpg://pyme_app:pyme_app_pass@localhost:5433/pyme_db
--
-- Las migraciones (alembic) y el scheduler usan pyme_user vía URL separada o
-- inyección de variable. Esto debe formalizarse en una segunda fase.
