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

import sys

import app.db.models.embeddings  # noqa — registra modelos en Base.metadata
import app.db.models.generative_ui  # noqa — registra GeneratedUI en Base.metadata
import app.db.models.models  # noqa — registra modelos en Base.metadata

print("[env] models imported", flush=True, file=sys.stderr)

from app.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Obtener DATABASE_URL del entorno (con driver async para SQLAlchemy asyncpg)
_database_url = os.environ.get("DATABASE_URL", "")

# Alembic necesita la URL correctamente configurada
if not _database_url:
    raise RuntimeError(
        "DATABASE_URL no está configurada. "
        "Asegúrate de que el archivo .env existe en backend/ o que la variable está en el entorno."
    )

# Guardar en el config para que offline mode también la use
config.set_main_option("sqlalchemy.url", _database_url)

target_metadata = Base.metadata


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
    # Use synchronous psycopg2 for migrations — more reliable than asyncpg+run_sync
    sync_url = _database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    import sys

    print("[env] creating engine", flush=True, file=sys.stderr)
    connectable = create_engine(sync_url, poolclass=pool.NullPool)
    print("[env] connecting", flush=True, file=sys.stderr)
    with connectable.connect() as connection:
        print("[env] configuring context", flush=True, file=sys.stderr)
        context.configure(connection=connection, target_metadata=target_metadata)
        print("[env] beginning transaction", flush=True, file=sys.stderr)
        with context.begin_transaction():
            print("[env] running migrations", flush=True, file=sys.stderr)
            context.run_migrations()
            print("[env] migrations done", flush=True, file=sys.stderr)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
