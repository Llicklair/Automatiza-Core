"""Tests de la clasificación pura de caducidad de lotes (sin base de datos)."""

from datetime import date

from app.services.alerts._expiry import expiry_status


def test_already_expired_is_error():
    severity, days = expiry_status(date(2026, 6, 1), date(2026, 6, 5))
    assert severity == "error"
    assert days == -4


def test_expires_today_is_warning():
    severity, days = expiry_status(date(2026, 6, 5), date(2026, 6, 5))
    assert severity == "warning"
    assert days == 0


def test_expires_soon_is_warning_with_days_left():
    severity, days = expiry_status(date(2026, 6, 12), date(2026, 6, 5))
    assert severity == "warning"
    assert days == 7
