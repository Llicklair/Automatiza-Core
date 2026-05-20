"""Extracción estructurada de facturas RECIBIDAS desde imagen o PDF.

Diferencia con receipt_scanner: aquí extraemos estructura COMPLETA — emisor
con NIF, líneas detalladas, IVA por tipo, vencimiento, número de factura.
Resultado pensado para crear un Invoice (invoice_type='received') con sus
InvoiceLine completas.

Estrategia: Claude Sonnet con vision (más capaz que Haiku para extracciones
estructuradas complejas con varias líneas y desglose IVA).
"""

from __future__ import annotations

import base64
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date

from app.core.config import settings

_log = logging.getLogger(__name__)

SUPPORTED_MIME = {
    "image/png", "image/jpeg", "image/webp", "image/gif",
    "application/pdf",
}

_PROMPT = """Eres un asistente que extrae datos estructurados de FACTURAS RECIBIDAS de proveedores en España.

Devuelve EXCLUSIVAMENTE este JSON, sin markdown ni texto adicional:

{
  "emisor": {
    "nif": string,           // CIF/NIF del proveedor (p.ej. B12345678 o 12345678X). Puede empezar por código país UE (FR..., DE...).
    "name": string,          // Razón social del emisor.
    "address": string|null,  // Dirección completa o null.
    "city": string|null,
    "postal_code": string|null
  },
  "invoice_number": string,  // Número/serie de la factura tal cual aparece.
  "issue_date": "YYYY-MM-DD",
  "due_date": "YYYY-MM-DD"|null,  // Si aparece o es deducible (ej. "30 días").
  "lines": [
    {
      "description": string,
      "quantity": number,    // 1 si no se indica
      "unit_price": number,  // Precio unitario sin IVA
      "tax_percentage": number, // 4, 10, 21 o 0
      "total": number        // Total línea con IVA
    }
  ],
  "amount_base": number,     // Base imponible total
  "tax_amount": number,      // Total IVA
  "amount_total": number,    // Total con IVA (lo que se paga)
  "currency": "EUR",
  "payment_method": string|null,   // "transferencia", "domiciliacion", "tarjeta"…
  "iban": string|null,             // IBAN si aparece para domiciliación
  "confidence": number             // 0.0 a 1.0
}

Reglas:
- Si una línea no tiene desglose, calcula unit_price = total / (1 + tax_percentage/100) / quantity.
- Si el total con IVA y la base no cuadran (±1€), prima el que aparece como TOTAL FACTURA.
- Si no ves IVA, asume tax_percentage=21 (régimen general).
- Si la factura es de un proveedor UE no español (NIF empezando por FR, DE, IT...), respeta su NIF sin convertir.

Si la imagen no es una factura legible o falta el total, devuelve:
{"error": "motivo breve"}
"""


@dataclass
class InvoiceLineExtracted:
    description: str
    quantity: float
    unit_price: float
    tax_percentage: float
    total: float

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "tax_percentage": self.tax_percentage,
            "total": self.total,
        }


@dataclass
class InvoiceExtracted:
    emisor_nif: str
    emisor_name: str
    emisor_address: str | None
    emisor_city: str | None
    emisor_postal_code: str | None
    invoice_number: str
    issue_date: date
    due_date: date | None
    lines: list[InvoiceLineExtracted]
    amount_base: float
    tax_amount: float
    amount_total: float
    currency: str
    payment_method: str | None
    iban: str | None
    confidence: float
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "emisor": {
                "nif": self.emisor_nif,
                "name": self.emisor_name,
                "address": self.emisor_address,
                "city": self.emisor_city,
                "postal_code": self.emisor_postal_code,
            },
            "invoice_number": self.invoice_number,
            "issue_date": self.issue_date.isoformat(),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "lines": [ln.to_dict() for ln in self.lines],
            "amount_base": self.amount_base,
            "tax_amount": self.tax_amount,
            "amount_total": self.amount_total,
            "currency": self.currency,
            "payment_method": self.payment_method,
            "iban": self.iban,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


class InvoiceExtractionError(RuntimeError):
    pass


def _parse_json_loose(text: str) -> dict:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise InvoiceExtractionError("La IA no devolvió un JSON parseable")
    return json.loads(match.group(0))


def _parse_date(s) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except (ValueError, TypeError):
        return None


def _build_invoice(payload: dict) -> InvoiceExtracted:
    if "error" in payload:
        raise InvoiceExtractionError(str(payload["error"]))

    emisor = payload.get("emisor") or {}
    emisor_nif = (emisor.get("nif") or "").strip()[:50]
    emisor_name = (emisor.get("name") or "").strip()[:255]
    if not emisor_nif:
        raise InvoiceExtractionError("No se pudo extraer el NIF del emisor.")
    if not emisor_name:
        raise InvoiceExtractionError("No se pudo extraer la razón social del emisor.")

    issue_d = _parse_date(payload.get("issue_date"))
    if issue_d is None:
        raise InvoiceExtractionError("No se pudo extraer la fecha de la factura.")
    due_d = _parse_date(payload.get("due_date"))

    raw_lines = payload.get("lines") or []
    if not isinstance(raw_lines, list) or not raw_lines:
        raise InvoiceExtractionError("La factura no tiene líneas detectables.")

    lines: list[InvoiceLineExtracted] = []
    for raw in raw_lines:
        try:
            lines.append(InvoiceLineExtracted(
                description=str(raw.get("description") or "")[:500] or "Concepto",
                quantity=float(raw.get("quantity") or 1),
                unit_price=float(raw.get("unit_price") or 0),
                tax_percentage=float(raw.get("tax_percentage") if raw.get("tax_percentage") is not None else 21),
                total=float(raw.get("total") or 0),
            ))
        except (TypeError, ValueError):
            continue

    try:
        amount_base = float(payload.get("amount_base") or 0)
        amount_total = float(payload.get("amount_total") or 0)
        tax_amount = float(payload.get("tax_amount") or max(0.0, amount_total - amount_base))
    except (TypeError, ValueError) as e:
        raise InvoiceExtractionError(f"Importes inválidos: {e}") from e

    warnings: list[str] = []
    # Validación de coherencia
    if amount_total > 0 and abs((amount_base + tax_amount) - amount_total) > 1.0:
        warnings.append(
            f"Importes incoherentes: base+IVA ({amount_base + tax_amount:.2f}) "
            f"≠ total ({amount_total:.2f}). Revisar manualmente."
        )

    return InvoiceExtracted(
        emisor_nif=emisor_nif,
        emisor_name=emisor_name,
        emisor_address=(emisor.get("address") or None),
        emisor_city=(emisor.get("city") or None),
        emisor_postal_code=(emisor.get("postal_code") or None),
        invoice_number=str(payload.get("invoice_number") or "")[:100] or "S/N",
        issue_date=issue_d,
        due_date=due_d,
        lines=lines,
        amount_base=round(amount_base, 2),
        tax_amount=round(tax_amount, 2),
        amount_total=round(amount_total, 2),
        currency=str(payload.get("currency") or "EUR")[:3],
        payment_method=(payload.get("payment_method") or None),
        iban=(payload.get("iban") or None),
        confidence=float(payload.get("confidence", 0.5)),
        warnings=warnings,
    )


async def extract_invoice_data(image_bytes: bytes, mime_type: str) -> InvoiceExtracted:
    """Procesa imagen o PDF de factura recibida y devuelve estructura completa.

    No crea el Invoice — devuelve borrador para que el frontend lo confirme.
    """
    if mime_type not in SUPPORTED_MIME:
        raise InvoiceExtractionError(
            f"Formato no soportado: {mime_type}. Usa PNG, JPG, WEBP o PDF."
        )

    if not image_bytes or len(image_bytes) < 500:
        raise InvoiceExtractionError("Fichero vacío o demasiado pequeño.")
    if len(image_bytes) > 10 * 1024 * 1024:
        raise InvoiceExtractionError("Fichero supera el límite de 10 MB.")

    api_key = getattr(settings, "ANTHROPIC_API_KEY", None)
    if not api_key:
        raise InvoiceExtractionError("Falta ANTHROPIC_API_KEY en configuración.")

    try:
        from anthropic import AsyncAnthropic
    except ImportError as e:
        raise InvoiceExtractionError("SDK anthropic no instalado.") from e

    client = AsyncAnthropic(api_key=api_key)
    image_b64 = base64.b64encode(image_bytes).decode("ascii")

    # Para facturas usamos Sonnet (más preciso que Haiku con líneas múltiples)
    model = getattr(settings, "ANTHROPIC_MODEL", None) or "claude-sonnet-4-6"

    # Anthropic vision admite PDF directamente como type=document desde finales 2024
    if mime_type == "application/pdf":
        content_block = {
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": image_b64},
        }
    else:
        content_block = {
            "type": "image",
            "source": {"type": "base64", "media_type": mime_type, "data": image_b64},
        }

    resp = await client.messages.create(
        model=model,
        max_tokens=2500,
        system=_PROMPT,
        messages=[{
            "role": "user",
            "content": [
                content_block,
                {"type": "text", "text": "Extrae los datos de esta factura recibida según el formato pedido."},
            ],
        }],
    )

    text_blocks = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    if not text_blocks:
        raise InvoiceExtractionError("La IA no devolvió contenido de texto.")

    payload = _parse_json_loose(text_blocks[0])
    _log.info(
        "Invoice extracted: emisor=%s num=%s total=%s",
        (payload.get("emisor") or {}).get("nif"),
        payload.get("invoice_number"),
        payload.get("amount_total"),
    )
    return _build_invoice(payload)
