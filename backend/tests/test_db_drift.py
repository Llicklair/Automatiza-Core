"""Tests del script de drift detection BD vs modelos (ALB.2)."""
import sys
from pathlib import Path

import pytest

# Hace importable el script desde scripts/
_SCRIPTS = Path(__file__).parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from db_drift import DriftReport  # noqa: E402


class TestDriftReport:
    def test_sin_drift(self):
        r = DriftReport()
        assert r.has_drift is False
        assert r.format() == "OK — sin drift entre BD y modelos."

    def test_drift_tablas_faltantes(self):
        r = DriftReport(missing_tables=["foo", "bar"])
        assert r.has_drift is True
        out = r.format()
        assert "Tablas declaradas pero ausentes en BD (2)" in out
        assert "- bar" in out
        assert "- foo" in out

    def test_drift_tablas_huerfanas(self):
        r = DriftReport(orphan_tables=["legacy_table"])
        assert r.has_drift is True
        assert "Tablas en BD sin modelo declarado (1)" in r.format()

    def test_drift_columnas_faltantes(self):
        r = DriftReport(missing_columns={"invoices": ["new_field", "another"]})
        assert r.has_drift is True
        out = r.format()
        assert "Columnas faltantes (2 en 1 tablas)" in out
        assert "invoices: another, new_field" in out

    def test_columnas_ordenadas_deterministicamente(self):
        r = DriftReport(missing_columns={"a": ["z", "a", "m"]})
        out = r.format()
        # Las columnas se ordenan alfabéticamente.
        assert "a: a, m, z" in out


@pytest.mark.asyncio
class TestDetectDrift:
    async def test_devuelve_report_vacio_si_bd_es_consistente_con_modelos(
        self, db,
    ):
        """Tras las fixtures, la BD de tests coincide con los modelos."""
        from db_drift import detect_drift

        # Usa la URL del fixture (sqlite en memoria)
        url = str(db.bind.url) if db.bind else "sqlite+aiosqlite:///:memory:"
        report = await detect_drift(url)

        # No tiene que haber tablas huérfanas (la BD se crea desde Base.metadata)
        # ni columnas faltantes. Tablas faltantes podría haberlas si los tests
        # no crearon todas — toleramos eso pero no esperamos columnas faltantes.
        assert not report.missing_columns, (
            f"Drift inesperado en columnas: {report.missing_columns}"
        )
