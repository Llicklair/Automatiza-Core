"""Lógica pura de clasificación de caducidad de lotes (sin base de datos)."""

from __future__ import annotations

from datetime import date

# Horizonte por defecto: avisar de lotes que caducan dentro de N días.
EXPIRY_HORIZON_DAYS = 7


def expiry_status(expiry_date: date, today: date) -> tuple[str, int]:
    """Clasifica un lote por su caducidad respecto a `today`.

    Devuelve `(severity, days_left)`:
      - `days_left` < 0  → ya caducado  → severity "error".
      - `days_left` >= 0 → caduca pronto → severity "warning".
    """
    days_left = (expiry_date - today).days
    severity = "error" if days_left < 0 else "warning"
    return severity, days_left
