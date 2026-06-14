"""Inicializa el schema de BD para CI: create_all desde modelos + stamp head.

El proyecto gestiona su schema con `create_all` desde los modelos (la ruta
"fresh install" del desktop, `_desktop_migrate.py`), NO con `alembic upgrade head`
paso a paso: la cadena de migraciones no es self-consistent desde una BD vacía
(hay tablas que solo existen en los modelos, p.ej. `work_schedules`, y revision
ids >32 chars). Este script reproduce esa ruta para el job de CI.

Importar `app.main` registra TODOS los modelos en `Base.metadata` (igual que
hace conftest), de modo que `create_all` cree el schema completo. Luego se
sella alembic a head para que el estado de migraciones quede consistente.
"""

import os
import sys

# CI corre desde `backend/` pero `python scripts/ci_init_db.py` no pone el cwd en
# sys.path → sin esto `import app.*` falla con ModuleNotFoundError.
sys.path.insert(0, os.getcwd())

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

import app.main  # noqa: F401 — registra TODOS los modelos en Base.metadata
from app.db.base import Base

sync_url = os.environ["DATABASE_URL"].replace("+asyncpg", "")
engine = create_engine(sync_url)
Base.metadata.create_all(engine)
command.stamp(Config("alembic.ini"), "head")
print("[CI] Schema creado desde modelos (create_all) + alembic stamped a head.")
