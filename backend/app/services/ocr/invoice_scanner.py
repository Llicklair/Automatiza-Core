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
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
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
            lines.append(
                InvoiceLineExtracted(
                    description=str(raw.get("description") or "")[:500] or "Concepto",
                    quantity=float(raw.get("quantity") or 1),
                    unit_price=float(raw.get("unit_price") or 0),
                    tax_percentage=float(raw.get("tax_percentage") if raw.get("tax_percentage") is not None else 21),
                    total=float(raw.get("total") or 0),
                )
            )
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


async def _resolve_vision_credentials(tenant_id, db) -> tuple[str, str, str | None] | None:
    """Resuelve una clave con VISIÓN para el tenant (modelo BYOK).

    Prefiere Anthropic (admite PDF + imagen), luego OpenAI (solo imagen).
    Busca en TODAS las ranuras del tenant (no solo el provider activo): así el
    escáner funciona aunque el provider activo sea claude_code (CLI, sin clave).
    Cae al .env global como último recurso. Devuelve (provider, api_key, model).
    """
    try:
        from sqlalchemy import select

        from app.db.models.models import TenantLlmConfig
        from app.services.encryption import decrypt_credentials

        res = await db.execute(select(TenantLlmConfig).where(TenantLlmConfig.tenant_id == tenant_id))
        cfg = res.scalar_one_or_none()
        if cfg and cfg.encrypted_keys:
            keys = decrypt_credentials(cfg.encrypted_keys)
            for prov in ("anthropic", "openai"):
                pdata = keys.get(prov) or {}
                if pdata.get("api_key"):
                    return prov, pdata["api_key"], pdata.get("model")
    except Exception as e:
        _log.warning("No se pudo resolver clave de visión del tenant: %s", e)

    if getattr(settings, "ANTHROPIC_API_KEY", None):
        return "anthropic", settings.ANTHROPIC_API_KEY, getattr(settings, "ANTHROPIC_MODEL", None)
    if getattr(settings, "OPENAI_API_KEY", None):
        return "openai", settings.OPENAI_API_KEY, getattr(settings, "OPENAI_MODEL", None)
    return None


async def _extract_anthropic(api_key, model, mime_type, image_b64, user_text) -> str:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=api_key)
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
        model=model or "claude-sonnet-4-6",
        max_tokens=2500,
        system=_PROMPT,
        messages=[{"role": "user", "content": [content_block, {"type": "text", "text": user_text}]}],
    )
    blocks = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    if not blocks:
        raise InvoiceExtractionError("La IA no devolvió contenido de texto.")
    return blocks[0]


async def _extract_openai(api_key, model, mime_type, image_b64, user_text) -> str:
    if mime_type == "application/pdf":
        raise InvoiceExtractionError(
            "Con OpenAI sube la factura como imagen (JPG/PNG). "
            "Para PDF directamente, configura una clave de Anthropic."
        )
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    resp = await client.chat.completions.create(
        model=model or "gpt-4o-mini",
        max_tokens=2500,
        messages=[
            {"role": "system", "content": _PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}},
                ],
            },
        ],
    )
    text = resp.choices[0].message.content
    if not text:
        raise InvoiceExtractionError("La IA no devolvió contenido de texto.")
    return text


def _extract_text_from_pdf(image_bytes: bytes) -> str:
    """Extrae el contenido de un PDF con OpenDataLoader (OCR + tablas + estructura)
    y fallback a pypdf. Devuelve markdown; '' si no se pudo extraer nada.

    Gracias al OCR de OpenDataLoader (JRE), también funciona con PDFs escaneados
    sin necesidad de una clave de visión — solo el Claude CLI para estructurar.
    """
    try:
        from app.services.pdf.parser import parse_pdf

        doc = parse_pdf(file_bytes=image_bytes)
        return (doc.markdown or "").strip()
    except Exception as e:  # noqa: BLE001
        _log.warning("parse_pdf no pudo extraer texto: %s", e)
        return ""


def _regex_candidates(text: str) -> dict[str, list[str]]:
    """Pistas para el LLM: NIF/CIF, IBAN, fechas e importes detectados por regex."""

    def uniq(seq):
        return list(dict.fromkeys(seq))

    out: dict[str, list[str]] = {}
    nifs = re.findall(r"\b([A-Z]\d{7}[0-9A-J]|\d{8}[A-Z]|[A-Z]\d{8})\b", text)
    ibans = re.findall(r"\bES\d{2}(?:[ ]?\d{4}){5}\b", text)
    dates = re.findall(r"\b\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}\b", text)
    amounts = re.findall(r"\b\d{1,3}(?:[.,]\d{3})*[.,]\d{2}\b", text)
    if nifs:
        out["NIF/CIF candidatos"] = uniq(nifs)[:5]
    if ibans:
        out["IBAN candidatos"] = uniq(ibans)[:3]
    if dates:
        out["Fechas candidatas"] = uniq(dates)[:6]
    if amounts:
        out["Importes candidatos"] = uniq(amounts)[-8:]
    return out


async def _extract_via_text(text, candidates, tenant_id, db, few_shot_hint) -> str:
    """Estructura una factura a partir de su TEXTO usando el LLM del tenant.

    Funciona con cualquier provider de texto, incluido Claude Code (CLI), porque
    no necesita visión: el texto + las pistas regex se le pasan al modelo.
    """
    from langchain_core.messages import HumanMessage, SystemMessage

    from app.core.llm_factory import get_llm_for_tenant

    llm = await get_llm_for_tenant(tenant_id, db, temperature=0, format_output="json")

    cand_block = ""
    if candidates:
        cand_block = "\n\nPistas extraídas automáticamente (verifícalas con el texto):\n" + "\n".join(
            f"- {k}: {', '.join(map(str, v))}" for k, v in candidates.items()
        )
    user = (
        (few_shot_hint + "\n\n" if few_shot_hint else "")
        + "Texto extraído de la factura (el orden puede estar alterado):\n\n"
        + text[:12000]
        + cand_block
        + "\n\nExtrae los datos según el formato JSON pedido."
    )
    resp = await llm.ainvoke([SystemMessage(content=_PROMPT), HumanMessage(content=user)])
    content = resp.content if isinstance(resp.content, str) else str(resp.content)
    if not content.strip():
        raise InvoiceExtractionError("La IA no devolvió contenido de texto.")
    return content


async def extract_invoice_data(
    image_bytes: bytes,
    mime_type: str,
    *,
    few_shot_hint: str | None = None,
    tenant_id=None,
    db=None,
) -> InvoiceExtracted:
    """Procesa imagen o PDF de factura recibida y devuelve estructura completa.

    No crea el Invoice — devuelve borrador para que el frontend lo confirme.

    Args:
        image_bytes: bytes del PNG/JPG/WEBP/PDF.
        mime_type: MIME del archivo.
        few_shot_hint: texto opcional con contexto del proveedor (extracción
            previa) que se añade al prompt como hint orientativo. Lo genera
            `supplier_learning.build_few_shot_block` cuando el NIF tiene
            template guardado.
    """
    if mime_type not in SUPPORTED_MIME:
        raise InvoiceExtractionError(f"Formato no soportado: {mime_type}. Usa PNG, JPG, WEBP o PDF.")

    if not image_bytes or len(image_bytes) < 500:
        raise InvoiceExtractionError("Fichero vacío o demasiado pequeño.")
    if len(image_bytes) > 10 * 1024 * 1024:
        raise InvoiceExtractionError("Fichero supera el límite de 10 MB.")

    creds = None
    if tenant_id is not None and db is not None:
        creds = await _resolve_vision_credentials(tenant_id, db)

    raw_text: str | None = None

    # Vía 1 — VISIÓN (la más precisa): requiere clave Anthropic u OpenAI.
    if creds is not None:
        provider, api_key, model = creds
        image_b64 = base64.b64encode(image_bytes).decode("ascii")
        user_text = "Extrae los datos de esta factura recibida según el formato pedido."
        if few_shot_hint:
            user_text = few_shot_hint + "\n\n" + user_text
        try:
            if provider == "openai":
                raw_text = await _extract_openai(api_key, model, mime_type, image_b64, user_text)
            else:
                raw_text = await _extract_anthropic(api_key, model, mime_type, image_b64, user_text)
        except ImportError as e:
            raise InvoiceExtractionError(f"SDK del proveedor '{provider}' no instalado.") from e

    # Vía 2 — TEXTO (sin clave de visión): OpenDataLoader (OCR + tablas, fallback
    # pypdf) extrae el contenido del PDF y el LLM del tenant (Claude Code CLI
    # incluido) lo estructura. Es el flujo "open data loader → CLI".
    elif mime_type == "application/pdf" and tenant_id is not None and db is not None:
        doc_text = _extract_text_from_pdf(image_bytes)
        if len(doc_text) >= 80:
            raw_text = await _extract_via_text(doc_text, _regex_candidates(doc_text), tenant_id, db, few_shot_hint)
        else:
            raise InvoiceExtractionError(
                "No se pudo extraer texto del PDF (ni con OCR). Si es un escaneo de "
                "baja calidad, prueba con una clave con visión (Anthropic) en "
                "Configuración → Claves API, o sube un PDF con mejor resolución."
            )

    # Imagen sin clave de visión: no hay OCR local → no se puede.
    else:
        raise InvoiceExtractionError(
            "Para imágenes (JPG/PNG) el escáner necesita una clave con visión "
            "(Anthropic u OpenAI) en Configuración → Claves API. Los PDF con texto "
            "sí funcionan con Claude Code (CLI)."
        )

    payload = _parse_json_loose(raw_text)
    _log.info(
        "Invoice extracted: emisor=%s num=%s total=%s",
        (payload.get("emisor") or {}).get("nif"),
        payload.get("invoice_number"),
        payload.get("amount_total"),
    )
    return _build_invoice(payload)
