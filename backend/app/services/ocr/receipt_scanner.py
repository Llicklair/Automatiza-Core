"""Extracción de datos estructurados desde imágenes de tickets/recibos.

Estrategia: una sola llamada Anthropic con vision. No usamos LangChain porque
es un round-trip aislado sin tools ni memoria — el SDK directo es más simple.
"""

from __future__ import annotations

import base64
import json
import logging
import re
from dataclasses import dataclass
from datetime import date

from app.core.config import settings

_log = logging.getLogger(__name__)

# Categorías permitidas por el modelo Expense (mantener sincronizado con db/models/hr.py)
ALLOWED_CATEGORIES = {"viaje", "dieta", "material", "formacion", "otro"}

SUPPORTED_MIME = {"image/png", "image/jpeg", "image/webp", "image/gif"}

_PROMPT = """Eres un asistente que extrae datos estructurados de tickets y recibos para registrarlos como gasto de empresa en España.

Devuelve EXCLUSIVAMENTE un objeto JSON con esta estructura, sin comentarios ni texto fuera del JSON:

{
  "amount": number,            // Importe TOTAL en euros (con IVA). Decimal con punto.
  "vat_amount": number|null,   // Importe del IVA si aparece desglosado, o null.
  "vat_rate": number|null,     // Tipo IVA aplicado (4, 10 o 21) o null si no se ve.
  "date": "YYYY-MM-DD",        // Fecha del ticket. Si solo ves DD/MM/YYYY conviértelo.
  "merchant": string,          // Nombre del comercio/proveedor.
  "merchant_nif": string|null, // NIF/CIF si aparece (formato A12345678 o 12345678X).
  "category": string,          // Una de: "viaje","dieta","material","formacion","otro".
  "description": string,       // Resumen breve (<=80 chars): "Comida en X" / "Combustible en Y".
  "confidence": number         // 0.0 a 1.0 — tu confianza en la extracción.
}

Reglas de categorización:
- Combustible, peaje, taxi, aparcamiento, billetes (tren/avión/bus), hotel → "viaje"
- Comida, bar, restaurante, cafetería → "dieta"
- Material de oficina, ferretería, equipamiento, software, hardware → "material"
- Cursos, libros técnicos, conferencias, certificaciones → "formacion"
- Cualquier otro → "otro"

Si la imagen no es un ticket/recibo legible o falta el importe total, devuelve:
{"error": "motivo breve"}
"""


@dataclass
class ReceiptData:
    amount: float
    date: date
    merchant: str
    description: str
    category: str
    vat_amount: float | None = None
    vat_rate: float | None = None
    merchant_nif: str | None = None
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "amount": self.amount,
            "vat_amount": self.vat_amount,
            "vat_rate": self.vat_rate,
            "date": self.date.isoformat(),
            "merchant": self.merchant,
            "merchant_nif": self.merchant_nif,
            "category": self.category,
            "description": self.description,
            "confidence": self.confidence,
        }


class ReceiptExtractionError(RuntimeError):
    """Falla al extraer datos del ticket (imagen ilegible, no es un ticket, etc.)."""


def _parse_json_loose(text: str) -> dict:
    """Extrae el primer objeto JSON del texto (tolerante a markdown fences)."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ReceiptExtractionError("La IA no devolvió un objeto JSON parseable")
    return json.loads(match.group(0))


def _build_receipt(payload: dict) -> ReceiptData:
    if "error" in payload:
        raise ReceiptExtractionError(str(payload["error"]))

    try:
        amount = float(payload["amount"])
    except (KeyError, TypeError, ValueError) as e:
        raise ReceiptExtractionError(f"Importe no válido en la respuesta: {e}") from e

    try:
        fecha = date.fromisoformat(str(payload["date"])[:10])
    except (KeyError, ValueError, TypeError):
        fecha = date.today()

    category = str(payload.get("category", "otro")).lower()
    if category not in ALLOWED_CATEGORIES:
        category = "otro"

    merchant = str(payload.get("merchant", "")).strip()[:120] or "Sin identificar"
    description = str(payload.get("description", "")).strip()[:200] or f"Ticket {merchant}"

    vat_amount = payload.get("vat_amount")
    vat_rate = payload.get("vat_rate")
    return ReceiptData(
        amount=round(amount, 2),
        date=fecha,
        merchant=merchant,
        description=description,
        category=category,
        vat_amount=float(vat_amount) if vat_amount is not None else None,
        vat_rate=float(vat_rate) if vat_rate is not None else None,
        merchant_nif=(payload.get("merchant_nif") or None),
        confidence=float(payload.get("confidence", 0.5)),
    )


async def extract_receipt_data(image_bytes: bytes, mime_type: str) -> ReceiptData:
    """Procesa una imagen de ticket y devuelve los datos estructurados.

    Lanza ReceiptExtractionError si la imagen no es legible o la IA no responde
    con un JSON válido.
    """
    if mime_type not in SUPPORTED_MIME:
        raise ReceiptExtractionError(
            f"Tipo de imagen no soportado: {mime_type}. Usa PNG, JPG o WEBP."
        )

    if not image_bytes or len(image_bytes) < 200:
        raise ReceiptExtractionError("La imagen está vacía o es demasiado pequeña.")

    if len(image_bytes) > 8 * 1024 * 1024:
        raise ReceiptExtractionError("La imagen supera el límite de 8 MB.")

    api_key = settings.ANTHROPIC_API_KEY if hasattr(settings, "ANTHROPIC_API_KEY") else None
    if not api_key:
        raise ReceiptExtractionError(
            "Falta ANTHROPIC_API_KEY en la configuración del backend."
        )

    try:
        from anthropic import AsyncAnthropic
    except ImportError as e:
        raise ReceiptExtractionError("SDK anthropic no instalado en backend.") from e

    client = AsyncAnthropic(api_key=api_key)
    image_b64 = base64.b64encode(image_bytes).decode("ascii")

    model = getattr(settings, "ANTHROPIC_MODEL", None) or "claude-haiku-4-5-20251001"

    resp = await client.messages.create(
        model=model,
        max_tokens=600,
        system=_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Extrae los datos del ticket adjunto en el JSON pedido.",
                    },
                ],
            }
        ],
    )

    text_blocks = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    if not text_blocks:
        raise ReceiptExtractionError("La IA no devolvió contenido de texto.")

    payload = _parse_json_loose(text_blocks[0])
    _log.info("Receipt extracted: merchant=%s amount=%s", payload.get("merchant"), payload.get("amount"))
    return _build_receipt(payload)
