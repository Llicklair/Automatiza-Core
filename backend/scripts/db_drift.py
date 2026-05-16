"""Detección de drift entre BD viva y Base.metadata (ALB.2).

Uso:
    python backend/scripts/db_drift.py [--db-url URL] [--exit-code]

Compara el esquema declarado en SQLAlchemy `Base.metadata` con el
introspectado desde la BD viva. Reporta tres tipos de drift:

  1. **Tablas faltantes en BD**: declaradas en modelos pero no existen.
     → Suele indicar migración no aplicada.
  2. **Tablas huérfanas en BD**: existen pero no hay modelo.
     → Tablas legacy, candidatas a DROP o a re-modelar.
  3. **Columnas faltantes**: la tabla existe pero faltan columnas.
     → Migración parcial o ALTER TABLE manual sin migration.

Se considera **NO drift**:
  - Tipos exactos (SQLAlchemy normaliza por dialect; un check de tipo
    rígido daría falsos positivos al comparar Postgres vs SQLite).
  - Índices/constraints adicionales en BD (los suele añadir Postgres
    automáticamente y no forman parte del schema declarado).

Salida:
  - Si no hay drift: imprime "OK" y `exit 0`.
  - Si hay drift: imprime un informe + `exit 1` (si --exit-code).

CI: este script se ejecuta antes de aplicar la baseline ALB.1 para
verificar que las BDs de testers previos coinciden con el modelo.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass, field

import app.db.models  # noqa: F401 — registra modelos en el metadata

# Carga todos los modelos para poblar Base.metadata.
from app.db.base import Base  # noqa: F401
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

DEFAULT_DB_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./test.db",
)


@dataclass
class DriftReport:
    missing_tables: list[str] = field(default_factory=list)
    orphan_tables: list[str] = field(default_factory=list)
    missing_columns: dict[str, list[str]] = field(default_factory=dict)

    @property
    def has_drift(self) -> bool:
        return bool(self.missing_tables or self.orphan_tables or self.missing_columns)

    def format(self) -> str:
        if not self.has_drift:
            return "OK — sin drift entre BD y modelos."

        lines = ["DRIFT detectado:"]
        if self.missing_tables:
            lines.append(f"\n  Tablas declaradas pero ausentes en BD ({len(self.missing_tables)}):")
            for t in sorted(self.missing_tables):
                lines.append(f"    - {t}")
        if self.orphan_tables:
            lines.append(f"\n  Tablas en BD sin modelo declarado ({len(self.orphan_tables)}):")
            for t in sorted(self.orphan_tables):
                lines.append(f"    - {t}")
        if self.missing_columns:
            total = sum(len(cs) for cs in self.missing_columns.values())
            lines.append(f"\n  Columnas faltantes ({total} en {len(self.missing_columns)} tablas):")
            for table, cols in sorted(self.missing_columns.items()):
                lines.append(f"    - {table}: {', '.join(sorted(cols))}")
        return "\n".join(lines)


# Tablas de infraestructura que no se modelan en SQLAlchemy (Alembic
# meta, RLS schema vacío, etc.) — ignorarlas para no marcar drift falso.
_IGNORED_TABLES: frozenset[str] = frozenset({
    "alembic_version",
    "spatial_ref_sys",       # PostGIS
})


async def detect_drift(db_url: str) -> DriftReport:
    """Compara `Base.metadata.tables` con introspección de la BD."""
    engine = create_async_engine(db_url)

    async with engine.begin() as conn:
        def _inspect(sync_conn):
            insp = inspect(sync_conn)
            db_tables = set(insp.get_table_names())
            db_columns = {t: {c["name"] for c in insp.get_columns(t)} for t in db_tables}
            return db_tables, db_columns

        db_tables, db_columns = await conn.run_sync(_inspect)

    # Filtra tablas infra
    db_tables = {t for t in db_tables if t not in _IGNORED_TABLES}

    declared = {name for name in Base.metadata.tables}
    declared_columns = {
        name: {c.name for c in tbl.columns}
        for name, tbl in Base.metadata.tables.items()
    }

    report = DriftReport()
    report.missing_tables = sorted(declared - db_tables)
    report.orphan_tables = sorted(db_tables - declared)

    for table in declared & db_tables:
        missing = declared_columns[table] - db_columns.get(table, set())
        if missing:
            report.missing_columns[table] = sorted(missing)

    await engine.dispose()
    return report


async def _main(args: argparse.Namespace) -> int:
    report = await detect_drift(args.db_url)
    print(report.format())
    if args.exit_code and report.has_drift:
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="ALB.2 — drift detection BD vs modelos")
    parser.add_argument(
        "--db-url",
        default=DEFAULT_DB_URL,
        help=f"URL de BD asyncpg/aiosqlite (default: {DEFAULT_DB_URL})",
    )
    parser.add_argument(
        "--exit-code",
        action="store_true",
        help="Salir con código 1 si hay drift (útil para CI)",
    )
    args = parser.parse_args()
    return asyncio.run(_main(args))


if __name__ == "__main__":
    sys.exit(main())
