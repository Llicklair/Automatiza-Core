"""Importador Holded API (MIG.2).

Holded expone una REST API en `https://api.holded.com/api/`. Endpoints
relevantes para la migración:
- `/invoicing/v1/documents/invoice` — facturas emitidas.
- `/invoicing/v1/contacts` — clientes/proveedores.

El cliente proporciona su API key (cabecera `key`). Esta capa solo se ocupa
de la **descarga + normalización** a `ImportRow`; la persistencia la hace
el wizard (MIG.3).

Para MVP el cliente HTTP es síncrono (httpx con timeout estricto) y el flujo
es paginado — Holded devuelve 100 docs por página. El job entero corre como
APScheduler one-shot tras confirmación del wizard.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.services.migration.csv_importer import ImportRow


HOLDED_BASE_URL = "https://api.holded.com/api/invoicing/v1"


@dataclass
class HoldedCredentials:
    api_key: str
    base_url: str = HOLDED_BASE_URL


def normalize_holded_contact(contact: dict[str, Any]) -> ImportRow:
    """Convierte un contacto Holded en `ImportRow` (kind=clients)."""
    canonical = {
        "nif": (contact.get("code") or contact.get("vatnumber") or "") or None,
        "name": contact.get("name") or None,
        "email": contact.get("email") or None,
        "phone": contact.get("phone") or None,
        "address": ", ".join(filter(None, [
            contact.get("address"), contact.get("city"),
            contact.get("postalCode"), contact.get("country"),
        ])) or None,
    }
    errors: list[str] = []
    if not canonical["nif"] and not canonical["name"]:
        errors.append("contacto Holded sin NIF ni nombre")
    return ImportRow(canonical=canonical, raw=contact, errors=errors)


def normalize_holded_invoice(doc: dict[str, Any]) -> ImportRow:
    """Convierte una factura Holded en `ImportRow` (kind=invoices).

    Holded entrega importes en céntimos y date como timestamp Unix.
    """
    from datetime import datetime, timezone

    def _from_cents(v: Any) -> Decimal | None:
        if v is None:
            return None
        try:
            return Decimal(v) / Decimal("100")
        except Exception:
            return None

    date_iso = None
    try:
        if doc.get("date"):
            date_iso = datetime.fromtimestamp(int(doc["date"]), tz=timezone.utc).date().isoformat()
    except (ValueError, TypeError, OSError):
        date_iso = None

    canonical: dict[str, str | Decimal | None] = {
        "invoice_number": doc.get("docNumber") or doc.get("number") or None,
        "date": date_iso,
        "client_nif": (doc.get("contactCode") or "") or None,
        "client_name": doc.get("contactName") or None,
        "amount_base": _from_cents(doc.get("subtotal")),
        "tax_amount": _from_cents(doc.get("tax")),
        "amount_total": _from_cents(doc.get("total")),
    }
    errors: list[str] = []
    if not canonical["invoice_number"]:
        errors.append("documento Holded sin docNumber")
    return ImportRow(canonical=canonical, raw=doc, errors=errors)
