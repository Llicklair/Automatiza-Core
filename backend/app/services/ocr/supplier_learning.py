"""Aprendizaje por proveedor para reducir consumo LLM en escaneos OCR (F2.5).

Tres mecanismos compuestos sobre la extracción base de [invoice_scanner.py]:

  1. **Cache por hash de archivo** — `lookup_cached` / `save_to_cache`. Si
     un PDF idéntico entra de nuevo, devolvemos la extracción anterior
     SIN llamar al LLM (ahorro 100% tokens).

  2. **Overrides aprendidos por NIF** — `apply_template_overrides`.
     Cuando el usuario corrige una extracción (`save_correction`),
     persistimos las diferencias para aplicarlas automáticamente en
     futuras facturas del mismo proveedor (tax_percentage habitual,
     renombrados de descripción).

  3. **Few-shot por NIF** — `build_few_shot_block` añade la última
     extracción exitosa del mismo proveedor como ejemplo al prompt. El
     LLM aprende patrones de formato/numeración SIN coste de fine-tune.

El servicio NO modifica `extract_invoice_data` por defecto — la función
mantiene su firma original. La integración se hace desde la ruta, que
pasa `tenant_id` + `db` para activar las tres capas si están disponibles.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.supplier_learning import InvoiceScanCache, SupplierInvoiceTemplate

_log = logging.getLogger(__name__)


def file_sha256(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()


# ─── Cache de archivos ──────────────────────────────────────────────────


async def lookup_cached(
    db: AsyncSession, tenant_id: UUID, file_hash: str
) -> dict | None:
    res = await db.execute(
        sa.select(InvoiceScanCache).where(
            InvoiceScanCache.tenant_id == tenant_id,
            InvoiceScanCache.file_hash == file_hash,
        )
    )
    row = res.scalar_one_or_none()
    if row is None:
        return None
    data = dict(row.extracted_data)
    data["_from_cache"] = True
    return data


async def save_to_cache(
    db: AsyncSession,
    tenant_id: UUID,
    file_hash: str,
    file_size: int,
    mime_type: str,
    extracted_data: dict,
) -> None:
    """Upsert: el UNIQUE (tenant_id, file_hash) garantiza una sola fila."""
    is_pg = db.bind.dialect.name == "postgresql"
    if is_pg:
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        stmt = (
            pg_insert(InvoiceScanCache)
            .values(
                tenant_id=tenant_id,
                file_hash=file_hash,
                file_size=file_size,
                mime_type=mime_type,
                extracted_data=extracted_data,
            )
            .on_conflict_do_nothing(constraint="uq_invoice_scan_cache_tenant_hash")
        )
        await db.execute(stmt)
    else:
        # SQLite: comprobar manualmente
        existing = await db.execute(
            sa.select(InvoiceScanCache.id).where(
                InvoiceScanCache.tenant_id == tenant_id,
                InvoiceScanCache.file_hash == file_hash,
            )
        )
        if existing.scalar_one_or_none() is None:
            db.add(
                InvoiceScanCache(
                    tenant_id=tenant_id,
                    file_hash=file_hash,
                    file_size=file_size,
                    mime_type=mime_type,
                    extracted_data=extracted_data,
                )
            )
    await db.commit()


# ─── Template por NIF ───────────────────────────────────────────────────


async def get_template(
    db: AsyncSession, tenant_id: UUID, supplier_nif: str
) -> SupplierInvoiceTemplate | None:
    nif = (supplier_nif or "").strip().upper()
    if not nif:
        return None
    res = await db.execute(
        sa.select(SupplierInvoiceTemplate).where(
            SupplierInvoiceTemplate.tenant_id == tenant_id,
            SupplierInvoiceTemplate.supplier_nif == nif,
        )
    )
    return res.scalar_one_or_none()


def apply_template_overrides(
    extraction: dict, template: SupplierInvoiceTemplate | None
) -> dict:
    """Aplica los overrides aprendidos sobre el dict de extracción.

    No muta el original — devuelve un dict nuevo. Usa coincidencia
    case-insensitive en `description_overrides`.
    """
    if template is None:
        return extraction

    result = json.loads(json.dumps(extraction, default=str))

    default_pct = template.default_tax_percentage
    overrides = template.description_overrides or {}

    for line in result.get("lines", []) or []:
        if default_pct is not None and not line.get("tax_percentage"):
            line["tax_percentage"] = float(default_pct)
        desc = (line.get("description") or "").strip()
        for pattern, replacement in overrides.items():
            if pattern.lower() in desc.lower():
                line["description"] = replacement
                break

    result.setdefault("_overrides_applied", []).append(template.supplier_nif)
    return result


def build_few_shot_block(template: SupplierInvoiceTemplate | None) -> str:
    """Genera un bloque de texto con la última extracción del mismo NIF
    para añadirlo como hint al prompt principal. Vacío si no hay datos.
    """
    if template is None or not template.last_extraction:
        return ""
    last = template.last_extraction
    last_clean = {
        "emisor_nif": (last.get("emisor") or {}).get("nif"),
        "invoice_number_format": (last.get("invoice_number") or "")[:40],
        "lines_sample": [
            {
                "description": (ln.get("description") or "")[:80],
                "tax_percentage": ln.get("tax_percentage"),
            }
            for ln in (last.get("lines") or [])[:3]
        ],
        "default_tax_percentage": (
            float(template.default_tax_percentage)
            if template.default_tax_percentage is not None
            else None
        ),
    }
    return (
        "Contexto del proveedor (extracción anterior, sólo orientativa, "
        "respeta la imagen actual si difiere):\n"
        + json.dumps(last_clean, ensure_ascii=False, indent=2)
    )


async def record_extraction(
    db: AsyncSession,
    tenant_id: UUID,
    extraction: dict,
) -> None:
    """Tras una extracción exitosa, actualiza el template del proveedor.

    Incrementa contador, refresca `last_extraction`, recalcula `avg_amount_total`.
    Si no hay NIF de emisor o es inválido → no hace nada.
    """
    emisor = extraction.get("emisor") or {}
    nif = (emisor.get("nif") or "").strip().upper()
    if not nif:
        return

    name = emisor.get("name")
    amount_total = extraction.get("amount_total") or 0
    try:
        amount_total = Decimal(str(amount_total))
    except Exception:
        amount_total = Decimal("0")

    template = await get_template(db, tenant_id, nif)
    if template is None:
        db.add(
            SupplierInvoiceTemplate(
                tenant_id=tenant_id,
                supplier_nif=nif,
                supplier_name=name,
                last_extraction=extraction,
                extractions_count=1,
                avg_amount_total=amount_total,
                last_seen_at=datetime.utcnow(),
            )
        )
    else:
        n = template.extractions_count or 0
        prev_avg = Decimal(template.avg_amount_total or 0)
        new_avg = (prev_avg * n + amount_total) / (n + 1) if (n + 1) else amount_total
        template.last_extraction = extraction
        template.extractions_count = n + 1
        template.avg_amount_total = new_avg
        template.last_seen_at = datetime.utcnow()
        if name and not template.supplier_name:
            template.supplier_name = name
    await db.commit()


# ─── Aprendizaje desde corrección del usuario ───────────────────────────


def diff_corrections(original: dict, corrected: dict) -> dict[str, Any]:
    """Compara extracción original vs corregida y deriva overrides
    reutilizables para el proveedor.

    Sólo registra patrones útiles a futuro:
      - `default_tax_percentage` si el usuario cambió el IVA en TODAS
        las líneas al mismo valor (señal fuerte de "este proveedor
        siempre va a tipo X").
      - `description_overrides` para descripciones que se renombraron.
    """
    out: dict[str, Any] = {}

    o_lines = original.get("lines") or []
    c_lines = corrected.get("lines") or []

    # default_tax_percentage: si TODAS las líneas (al menos una) cambiaron
    # el tax_percentage al mismo valor.
    same_len = len(o_lines) == len(c_lines) and o_lines
    if same_len:
        rates_diff = [
            (o.get("tax_percentage"), c.get("tax_percentage"))
            for o, c in zip(o_lines, c_lines, strict=True)
        ]
        if all(c is not None and o != c for o, c in rates_diff):
            new_rates = {c for _, c in rates_diff}
            if len(new_rates) == 1:
                out["default_tax_percentage"] = float(new_rates.pop())

    # description_overrides: pares (original_strip, corrected_strip)
    desc_overrides: dict[str, str] = {}
    if same_len:
        for o, c in zip(o_lines, c_lines, strict=True):
            od = (o.get("description") or "").strip()
            cd = (c.get("description") or "").strip()
            if od and cd and od != cd:
                desc_overrides[od] = cd
    if desc_overrides:
        out["description_overrides"] = desc_overrides

    return out


async def save_correction(
    db: AsyncSession,
    tenant_id: UUID,
    supplier_nif: str,
    original: dict,
    corrected: dict,
) -> dict[str, Any]:
    """Persiste los overrides derivados de la corrección. Devuelve el
    diff aplicado para que el frontend lo muestre como confirmación.
    """
    nif = (supplier_nif or "").strip().upper()
    if not nif:
        return {}

    overrides = diff_corrections(original, corrected)
    if not overrides:
        return {}

    template = await get_template(db, tenant_id, nif)
    if template is None:
        template = SupplierInvoiceTemplate(
            tenant_id=tenant_id,
            supplier_nif=nif,
            supplier_name=(corrected.get("emisor") or {}).get("name"),
        )
        db.add(template)

    if "default_tax_percentage" in overrides:
        template.default_tax_percentage = Decimal(
            str(overrides["default_tax_percentage"])
        )
    if "description_overrides" in overrides:
        merged = dict(template.description_overrides or {})
        merged.update(overrides["description_overrides"])
        template.description_overrides = merged

    await db.commit()
    return overrides
