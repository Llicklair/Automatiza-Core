"""Shared parsing helpers for invoice agent tools."""
import re
from decimal import Decimal, InvalidOperation


def parse_amount_str(raw: str) -> tuple[Decimal, str | None]:
    """Parse a Spanish-format amount string to Decimal.

    Handles '1500.00' and '1.500,00' (thousand-separator dot) formats.
    Returns (Decimal, None) on success, or (Decimal('0'), error_msg) on failure.
    """
    s = raw.strip()
    if re.search(r"\.\d{3}(?:[,\d]|$)", s):
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return Decimal(s), None
    except (InvalidOperation, Exception):
        return Decimal("0"), f"Error: Importe no válido: '{raw}'. Usa formato '1500.00'."
