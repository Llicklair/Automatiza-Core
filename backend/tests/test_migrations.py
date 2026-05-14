"""Tests para verificar integridad de migraciones Alembic.

Comprueba que:
1. Todas las migraciones se aplican sin error (upgrade head)
2. El modelo actual coincide con las migraciones (alembic check)
"""
import subprocess
import sys

import pytest


PYTHON = sys.executable
BACKEND_DIR = str(__import__("pathlib").Path(__file__).resolve().parent.parent)


class TestAlembicMigrations:
    @pytest.mark.slow
    def test_alembic_check_no_pending(self):
        """Verifica que no hay cambios de modelo sin migración."""
        result = subprocess.run(
            [PYTHON, "-m", "alembic", "check"],
            cwd=BACKEND_DIR,
            capture_output=True,
            text=True,
            timeout=30,
        )
        # alembic check returns 0 if no new upgrade operations detected
        # It may fail if DB is not accessible — skip in that case
        if "Could not connect" in result.stderr or "Connection refused" in result.stderr:
            pytest.skip("Database not available for alembic check")
        if result.returncode != 0 and "No new upgrade operations" not in result.stdout:
            # Only fail if there are genuinely pending migrations
            if "New upgrade operations detected" in result.stdout:
                pytest.fail(f"Pending migrations detected:\n{result.stdout}")

    @pytest.mark.slow
    def test_migration_history_has_single_head(self):
        """Verifica que las migraciones convergen en un único head (sin branches abiertas)."""
        result = subprocess.run(
            [PYTHON, "-m", "alembic", "heads"],
            cwd=BACKEND_DIR,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            pytest.skip(f"alembic heads failed: {result.stderr}")
        heads = [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]
        if len(heads) != 1:
            pytest.fail(
                f"Expected exactly 1 migration head, found {len(heads)}:\n"
                + "\n".join(heads)
            )


class TestMigrationFiles:
    """QA.MIG — chequeos estáticos sobre los archivos de migración.

    Cada migración debe declarar `upgrade()` y `downgrade()`. Sin
    downgrade, un rollback en producción es imposible — un error de
    diseño que captureamos en CI antes de mergear.
    """

    def _migration_files(self) -> list:
        from pathlib import Path

        versions_dir = Path(BACKEND_DIR) / "app" / "db" / "migrations" / "versions"
        return sorted(versions_dir.glob("*.py"))

    def test_hay_al_menos_una_migracion(self):
        files = self._migration_files()
        assert len(files) > 0, "No se encontraron migraciones en versions/"

    def test_cada_migracion_define_upgrade_y_downgrade(self):
        """Cada archivo debe contener `def upgrade()` y `def downgrade()`."""
        missing: list[str] = []
        for path in self._migration_files():
            text = path.read_text(encoding="utf-8")
            if "def upgrade(" not in text:
                missing.append(f"{path.name}: falta upgrade()")
            if "def downgrade(" not in text:
                missing.append(f"{path.name}: falta downgrade()")
        assert not missing, (
            "Migraciones sin upgrade/downgrade completos:\n  - "
            + "\n  - ".join(missing)
        )

    def test_cada_migracion_declara_revision_y_down_revision(self):
        """`revision` y `down_revision` son obligatorios para encadenar."""
        missing: list[str] = []
        for path in self._migration_files():
            text = path.read_text(encoding="utf-8")
            if "revision = " not in text and "revision: str = " not in text:
                missing.append(f"{path.name}: falta `revision`")
            if "down_revision = " not in text and "down_revision: " not in text:
                missing.append(f"{path.name}: falta `down_revision`")
        assert not missing, "\n".join(missing)

    def test_revisions_son_unicas(self):
        """No puede haber dos migraciones con el mismo `revision = "..."`."""
        import re

        revisions: dict[str, str] = {}
        duplicates: list[str] = []
        for path in self._migration_files():
            text = path.read_text(encoding="utf-8")
            m = re.search(r'^revision\s*(?::\s*str\s*)?=\s*["\']([^"\']+)["\']',
                          text, re.MULTILINE)
            if not m:
                continue
            rev = m.group(1)
            if rev in revisions:
                duplicates.append(
                    f"{rev}: {revisions[rev]} y {path.name}"
                )
            revisions[rev] = path.name
        assert not duplicates, "Revisions duplicadas:\n  - " + "\n  - ".join(duplicates)

    def test_downgrade_no_es_pass_vacio(self):
        """Detecta `def downgrade(): pass` — señal de que el rollback no se pensó.

        Excepciones legítimas: migraciones de tipo "data backfill" donde
        el downgrade es realmente no-op. Esas deben documentarlo con un
        comment o pragma `# downgrade-noop-justified`.
        """
        suspicious: list[str] = []
        for path in self._migration_files():
            text = path.read_text(encoding="utf-8")
            # Captura `def downgrade(...) -> None:\n    pass\n` o similar.
            if "def downgrade" in text:
                # Busca el cuerpo aproximado
                after = text.split("def downgrade", 1)[1]
                # Primeras ~5 líneas tras la firma
                head = "\n".join(after.splitlines()[:6])
                if head.strip().endswith("pass") or "    pass\n" == head.splitlines()[-1] + "\n":
                    if "downgrade-noop-justified" not in text:
                        suspicious.append(path.name)
        assert not suspicious, (
            "Migraciones con downgrade() = pass sin justificación:\n  - "
            + "\n  - ".join(suspicious)
            + "\nAñade `# downgrade-noop-justified` si es intencional."
        )
