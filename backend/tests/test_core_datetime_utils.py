"""Tests para app.core.datetime_utils.as_aware.

Documenta el contrato del helper que centraliza la corrección del bug
tz-naive vs tz-aware detectado en recovery.py y approval.py (iter 2026-05-19).
"""

from datetime import datetime, timezone

import pytest
from app.core.datetime_utils import as_aware


class TestAsAware:
    def test_none_devuelve_none(self):
        assert as_aware(None) is None

    def test_naive_se_marca_como_utc(self):
        naive = datetime(2026, 5, 19, 12, 0, 0)
        result = as_aware(naive)
        assert result is not None
        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc
        # mismos componentes
        assert result.replace(tzinfo=None) == naive

    def test_aware_no_se_modifica(self):
        """Idempotencia: pasar un aware datetime devuelve el mismo objeto."""
        aware = datetime(2026, 5, 19, 12, 0, 0, tzinfo=timezone.utc)
        result = as_aware(aware)
        assert result is aware

    def test_aware_con_otro_tz_no_se_modifica(self):
        """No re-marca a UTC si ya tiene tz, aunque sea distinto."""
        from datetime import timedelta
        cet = timezone(timedelta(hours=2))
        aware_cet = datetime(2026, 5, 19, 14, 0, 0, tzinfo=cet)
        result = as_aware(aware_cet)
        assert result is aware_cet
        assert result.tzinfo == cet  # NO se convirtió a UTC

    def test_default_tz_alternativo(self):
        from datetime import timedelta
        cet = timezone(timedelta(hours=2))
        naive = datetime(2026, 5, 19, 12, 0, 0)
        result = as_aware(naive, default_tz=cet)
        assert result is not None
        assert result.tzinfo == cet

    def test_idempotente(self):
        """Aplicar dos veces da el mismo resultado."""
        naive = datetime(2026, 5, 19, 12, 0, 0)
        once = as_aware(naive)
        twice = as_aware(once)
        assert once == twice
        assert once is twice  # segundo paso es no-op

    def test_permite_comparar_con_now_utc(self):
        """Caso de uso real: comparar tras coerción no lanza TypeError."""
        naive = datetime(2026, 5, 19, 12, 0, 0)
        now_utc = datetime.now(timezone.utc)
        # Sin as_aware esto lanza TypeError
        coerced = as_aware(naive)
        assert coerced is not None
        # Esta comparación NO debe lanzar:
        _ = coerced < now_utc  # noqa: pointless statement, only check no error
