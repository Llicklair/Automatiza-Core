"""Pre-commit hook: exige migración si el commit toca `db/models/` (ALB.6).

Uso desde git pre-commit:
    python backend/scripts/check_migration.py

Sale con código 1 si el staging incluye cambios en
`backend/app/db/models/**.py` SIN incluir tambien al menos un archivo
nuevo o modificado en `backend/app/db/migrations/versions/**.py`.

Diseño:
- No bloquea cambios que solo añadan docstrings o constantes (vía
  heurística: solo se considera "modificación significativa" si hay
  diff que toque líneas con `Column(`, `__tablename__`, o `relationship`).
- Permite override con commit message que contenga `[skip-migration-check]`
  o variable de entorno `SKIP_MIGRATION_CHECK=1`. Documentar uso
  excepcional (renombrar variable interna, mover imports).

CI alternativo: el mismo script puede ejecutarse en GitHub Actions
contra el diff de la PR comparando con `origin/main`.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

MODELS_PATTERN = re.compile(r"^backend/app/db/models/.*\.py$")
MIGRATIONS_PATTERN = re.compile(
    r"^backend/app/db/migrations/versions/.*\.py$"
)
# Líneas que indican cambio estructural relevante (no solo doc/constants).
SCHEMA_SIGNIFICANT = re.compile(
    r"(Column\(|__tablename__|relationship\(|ForeignKey\(|Index\(|UniqueConstraint\()"
)

SKIP_MARKER = "[skip-migration-check]"


def _staged_files(diff_filter: str = "ACMR") -> list[str]:
    """Lista archivos staged. `diff_filter` filtra Added/Copied/Modified/Renamed."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", f"--diff-filter={diff_filter}"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _staged_diff(path: str) -> str:
    """Diff staged completo para un archivo concreto."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--unified=0", "--", path],
        capture_output=True, text=True, check=False,
    )
    return result.stdout if result.returncode == 0 else ""


def _commit_message_marker_present() -> bool:
    """True si el COMMIT_EDITMSG ya contiene el opt-out."""
    # En un hook prepare-commit-msg / commit-msg, $1 es el path.
    # En pre-commit no hay msg aún — el flag se debe pasar vía env var.
    msg_path = os.environ.get("COMMIT_MSG_FILE")
    if msg_path and Path(msg_path).exists():
        return SKIP_MARKER in Path(msg_path).read_text(encoding="utf-8")
    return False


def check_staged() -> tuple[bool, str]:
    """Devuelve (ok, mensaje). ok=True significa "pasa el hook"."""
    if os.environ.get("SKIP_MIGRATION_CHECK") == "1":
        return True, "Override SKIP_MIGRATION_CHECK=1 — saltando check."
    if _commit_message_marker_present():
        return True, "Override [skip-migration-check] en commit message — saltando."

    staged = _staged_files()
    model_changes = [f for f in staged if MODELS_PATTERN.match(f)]
    migration_changes = [f for f in staged if MIGRATIONS_PATTERN.match(f)]

    if not model_changes:
        return True, "Sin cambios en db/models/ — nada que verificar."

    # Heurística: solo bloquear si el diff toca líneas relevantes de schema.
    significant_models = []
    for path in model_changes:
        diff = _staged_diff(path)
        if any(
            SCHEMA_SIGNIFICANT.search(line)
            for line in diff.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        ):
            significant_models.append(path)

    if not significant_models:
        return True, (
            f"Cambios en {len(model_changes)} archivos de modelos sin tocar "
            "Column/__tablename__/relationship — no se exige migración."
        )

    if migration_changes:
        return True, (
            f"OK — {len(significant_models)} archivos de modelos con "
            f"{len(migration_changes)} migraciones acompañantes."
        )

    return False, (
        "FALLA: el commit modifica modelos SQLAlchemy con cambios estructurales "
        "pero NO incluye ninguna migración Alembic.\n\n"
        f"Modelos afectados:\n"
        + "\n".join(f"  - {f}" for f in significant_models)
        + "\n\nAcciones posibles:\n"
        "  1. Crear migración: `alembic revision --autogenerate -m 'descripción'`\n"
        "  2. Si el cambio NO afecta esquema (rename interno, docstring, etc.):\n"
        "     - Añade `[skip-migration-check]` al mensaje de commit, O\n"
        "     - Ejecuta con `SKIP_MIGRATION_CHECK=1 git commit ...`"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="ALB.6 — pre-commit migration check")
    parser.add_argument(
        "--verbose", action="store_true",
        help="Imprime detalles incluso cuando pasa",
    )
    args = parser.parse_args()

    ok, msg = check_staged()
    if not ok:
        print(msg, file=sys.stderr)
        return 1
    if args.verbose:
        print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
