#!/bin/sh
# Crea el rol de APLICACIÓN (pyme_app) separado del owner (pyme_user).
# Clave para que las políticas RLS apliquen al runtime (un owner las salta).
# Solo corre en el PRIMER arranque del volumen de datos (docker-entrypoint-initdb.d).
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE pyme_app LOGIN PASSWORD '${APP_DB_PASSWORD}';
    GRANT CONNECT ON DATABASE pyme_db TO pyme_app;
    GRANT USAGE ON SCHEMA public TO pyme_app;
    ALTER DEFAULT PRIVILEGES FOR ROLE pyme_user IN SCHEMA public
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO pyme_app;
    ALTER DEFAULT PRIVILEGES FOR ROLE pyme_user IN SCHEMA public
        GRANT USAGE, SELECT ON SEQUENCES TO pyme_app;
EOSQL
