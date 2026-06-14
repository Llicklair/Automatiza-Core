import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool

# ── Cargar .env automáticamente (para migraciones CLI sin variables de entorno) ──
try:
    from dotenv import load_dotenv

    # env.py lives at: backend/app/db/migrations/env.py
    # parents[0]=migrations, [1]=db, [2]=app, [3]=backend/
    _env_file = Path(__file__).resolve().parents[3] / ".env"
    if _env_file.exists():
        load_dotenv(_env_file)
    else:
        # fallback: buscar en el directorio de trabajo actual
        load_dotenv()
except ImportError:
    pass  # python-dotenv no instalado — se asume que DATABASE_URL ya está en el entorno

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Las migraciones corren con el rol ADMIN (privilegiado), NUNCA con el rol de
# aplicación pyme_app (NOSUPERUSER, no puede hacer DDL ni CREATE ROLE). Orden de
# preferencia: ADMIN_DATABASE_URL del entorno → DATABASE_URL del entorno (compat
# / despliegues no-desktop donde apunta al rol admin) → settings.ADMIN_DATABASE_URL.
_database_url = os.environ.get("ADMIN_DATABASE_URL") or os.environ.get("DATABASE_URL", "")

if not _database_url:
    try:
        from app.core.config import settings

        _database_url = settings.ADMIN_DATABASE_URL
    except Exception:
        pass

# Alembic necesita la URL correctamente configurada
if not _database_url:
    raise RuntimeError(
        "Ni ADMIN_DATABASE_URL ni DATABASE_URL están configuradas. "
        "Asegúrate de que el archivo .env existe en backend/ o que la variable está en el entorno."
    )

# Guardar en el config para que offline mode también la use
config.set_main_option("sqlalchemy.url", _database_url)

# target_metadata se usa sólo para autogenerate (alembic revision --autogenerate).
# Para upgrade/check no es necesario y cargarlo aquí provoca que app.db.base
# cree un async engine con asyncpg a nivel de módulo, lo que cuelga las migraciones en CI.
# Para usar autogenerate localmente, importa los modelos manualmente aquí.
target_metadata = None


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    sync_url = _database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    connectable = create_engine(sync_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        connection = connection.execution_options(isolation_level="AUTOCOMMIT")
        # Los revision ids descriptivos superan los 32 chars por defecto de
        # alembic_version.version_num (p.ej. 0032_employee_memory_and_rag_scope = 34).
        # Garantizamos la columna ANCHA antes de migrar — BD nuevas (CREATE) y
        # existentes (ALTER) — para evitar StringDataRightTruncation al hacer
        # `alembic upgrade head` paso a paso. El bootstrap desktop ya lo hacía;
        # esto lo cubre también en CI y dev.
        if connection.dialect.name == "postgresql":
            connection.exec_driver_sql(
                "CREATE TABLE IF NOT EXISTS alembic_version ("
                "version_num VARCHAR(128) NOT NULL, "
                "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
            )
            connection.exec_driver_sql(
                "ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)"
            )
        context.configure(connection=connection, target_metadata=target_metadata)
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
