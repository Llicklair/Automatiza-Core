"""Tests del pre-commit hook ALB.6."""
import sys
from pathlib import Path
from unittest.mock import patch

_SCRIPTS = Path(__file__).parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import check_migration  # noqa: E402


class TestCheckStaged:
    def test_sin_cambios_en_modelos_pasa(self):
        with patch.object(check_migration, "_staged_files", return_value=[
            "backend/app/api/v1/routes/system.py",
            "frontend/src/lib/api/onboarding.ts",
        ]):
            ok, msg = check_migration.check_staged()
        assert ok is True
        assert "Sin cambios en db/models/" in msg

    def test_modelo_con_column_y_sin_migration_falla(self):
        with patch.object(
            check_migration, "_staged_files",
            return_value=["backend/app/db/models/billing.py"],
        ), patch.object(
            check_migration, "_staged_diff",
            return_value="+    new_field = Column(String(50), nullable=True)\n",
        ):
            ok, msg = check_migration.check_staged()
        assert ok is False
        assert "FALLA" in msg
        assert "billing.py" in msg

    def test_modelo_con_migration_acompanante_pasa(self):
        def fake_files():
            return [
                "backend/app/db/models/billing.py",
                "backend/app/db/migrations/versions/0024_new.py",
            ]

        with patch.object(check_migration, "_staged_files", side_effect=fake_files), \
             patch.object(
                check_migration, "_staged_diff",
                return_value="+    new_field = Column(String(50))\n",
            ):
            ok, msg = check_migration.check_staged()
        assert ok is True
        assert "migraciones acompañantes" in msg

    def test_modelo_solo_docstring_no_exige_migration(self):
        """Cambio sin tocar Column/__tablename__/relationship → pasa."""
        with patch.object(
            check_migration, "_staged_files",
            return_value=["backend/app/db/models/billing.py"],
        ), patch.object(
            check_migration, "_staged_diff",
            return_value='+    """Comentario nuevo en el docstring."""\n',
        ):
            ok, msg = check_migration.check_staged()
        assert ok is True
        assert "no se exige migración" in msg

    def test_override_env_var(self, monkeypatch):
        monkeypatch.setenv("SKIP_MIGRATION_CHECK", "1")
        # Aunque se tocan modelos sin migration, el override hace pasar.
        with patch.object(
            check_migration, "_staged_files",
            return_value=["backend/app/db/models/billing.py"],
        ), patch.object(
            check_migration, "_staged_diff",
            return_value="+    new_col = Column(String)\n",
        ):
            ok, msg = check_migration.check_staged()
        assert ok is True
        assert "Override SKIP_MIGRATION_CHECK" in msg

    def test_relationship_es_significativo(self):
        with patch.object(
            check_migration, "_staged_files",
            return_value=["backend/app/db/models/crm.py"],
        ), patch.object(
            check_migration, "_staged_diff",
            return_value='+    invoices = relationship("Invoice")\n',
        ):
            ok, msg = check_migration.check_staged()
        # relationship es señal de cambio de schema relacional.
        assert ok is False

    def test_foreign_key_es_significativo(self):
        with patch.object(
            check_migration, "_staged_files",
            return_value=["backend/app/db/models/billing.py"],
        ), patch.object(
            check_migration, "_staged_diff",
            return_value='+    user_id = Column(UUID, ForeignKey("users.id"))\n',
        ):
            ok, msg = check_migration.check_staged()
        assert ok is False
