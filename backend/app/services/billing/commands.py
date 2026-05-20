"""Billing commands â€” write operations (CQRS-lite).

All functions here produce side effects: INSERT/UPDATE/DELETE or file writes.
Read helpers are imported from queries.py to avoid duplication.
"""

import logging
import os
import uuid as uuid_mod
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.db.models.models import (
    FixedAsset,
    Invoice,
    InvoiceLine,
    InvoiceSeries,
    JournalEntry,
    JournalLine,
    RecurringInvoice,
    Tenant,
    TenantDocument,
)
from app.services.billing.queries import (
    UPLOAD_DIR,
    VALID_IVA,
    _build_invoice_data,
    _load_invoice,
)

logger = logging.getLogger(__name__)


# â”€â”€ Invoice commands â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


async def create_invoice(
    client_id: UUID,
    payload_dict: dict,
    lines_data: list[dict],
    tenant_id,
    user_id,
    db: AsyncSession,
):
    """Crea factura con líneas. Lanza ValueError si IVA inválido o total negativo."""
    for k in ("amount_base", "tax_amount", "amount_total"):
        payload_dict.pop(k, None)

    manual_number = payload_dict.pop("invoice_number", None)
    serie = (payload_dict.pop("serie", "F") or "F").upper()[:10]

    if manual_number:
        invoice_number = manual_number
    else:
        invoice_year = datetime.now(UTC).year
        series_result = await db.execute(
            select(InvoiceSeries)
            .where(
                InvoiceSeries.tenant_id == tenant_id,
                InvoiceSeries.serie == serie,
                InvoiceSeries.year == invoice_year,
            )
            .with_for_update()
        )
        series_row = series_result.scalar_one_or_none()

        if series_row is None:
            series_row = InvoiceSeries(
                tenant_id=tenant_id,
                serie=serie,
                year=invoice_year,
                last_number=0,
                prefix=serie,
            )
            db.add(series_row)
            await db.flush()

        series_row.last_number += 1
        invoice_number = f"{series_row.prefix}{invoice_year}-{series_row.last_number:04d}"

    new_invoice = Invoice(
        tenant_id=tenant_id,
        client_id=client_id,
        invoice_number=invoice_number,
        amount_base=0.0,
        tax_amount=0.0,
        amount_total=0.0,
        **payload_dict,
    )
    db.add(new_invoice)
    await db.commit()
    await db.refresh(new_invoice)

    total_base = 0.0
    total_tax = 0.0

    for line_data in lines_data:
        qty = float(line_data.get("quantity", 1))
        uprice = float(line_data.get("unit_price", 0))
        discount_perc = float(line_data.get("discount_percentage", 0))
        tax_perc = float(line_data.get("tax_percentage", 21))

        if tax_perc not in VALID_IVA:
            raise ValueError(
                f"Tipo de IVA inválido: {tax_perc}%. Los valores permitidos son: 0%, 4%, 10%, 21%."
            )

        line_base = qty * uprice
        if discount_perc > 0:
            line_base -= line_base * (discount_perc / 100)
        line_tax = line_base * (tax_perc / 100)
        line_total = line_base + line_tax

        total_base += line_base
        total_tax += line_tax

        db.add(
            InvoiceLine(
                invoice_id=new_invoice.id,
                product_id=line_data.get("product_id"),
                description=line_data.get("description"),
                quantity=qty,
                unit_price=uprice,
                discount_percentage=discount_perc,
                tax_percentage=tax_perc,
                total=line_total,
            )
        )

    new_invoice.amount_base = round(total_base, 2)
    new_invoice.tax_amount = round(total_tax, 2)
    new_invoice.amount_total = round(total_base + total_tax, 2)

    if new_invoice.amount_total < 0:
        await db.rollback()
        raise ValueError("El importe total de la factura no puede ser negativo.")
    if lines_data and new_invoice.amount_total == 0:
        logger.warning("Factura creada con importe 0 para cliente %s", client_id)

    # Verifactu: si el tenant está en modo "voluntary" creamos la entrada
    # encadenada ANTES del commit, así la factura y su huella son atómicas.
    # En modo "no_remission" no hace nada.
    from app.services.billing.verifactu_chain import maybe_append_verifactu_record
    await maybe_append_verifactu_record(db, invoice=new_invoice)

    await db.commit()

    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.client), joinedload(Invoice.lines))
        .where(Invoice.id == new_invoice.id)
    )
    return result.unique().scalar_one()


async def update_status(
    invoice_id: UUID,
    tenant_id,
    new_status: str,
    db: AsyncSession,
):
    """Cambia estado. Lanza ValueError si no existe o estado inválido."""
    allowed = {"draft", "pending", "paid", "cancelled"}
    if new_status not in allowed:
        raise ValueError(f"Estado no válido. Opciones: {allowed}")

    invoice = await _load_invoice(invoice_id, tenant_id, db)
    if not invoice:
        raise ValueError("Factura no encontrada")

    invoice.status = new_status
    await db.commit()
    await db.refresh(invoice)
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.client), joinedload(Invoice.lines))
        .where(Invoice.id == invoice_id)
    )
    return result.unique().scalar_one()


async def delete_invoice(invoice_id: UUID, tenant_id, db: AsyncSession) -> bool:
    invoice = await _load_invoice(invoice_id, tenant_id, db, with_joins=False)
    if not invoice:
        return False
    await db.delete(invoice)
    await db.commit()
    return True


async def generate_and_save_invoice_pdf(invoice, tenant_id, user_id) -> None:
    """Genera el PDF y lo registra como TenantDocument (background task)."""
    from app.db.base import AsyncSessionLocal
    from app.services.pdf import generate_invoice_pdf
    from app.services.template_service import get_default_theme

    try:
        async with AsyncSessionLocal() as session:
            tenant_obj = await session.get(Tenant, tenant_id)
            theme_config = await get_default_theme(tenant_id, "invoice", session)

        company_name = tenant_obj.name if tenant_obj else "Mi Empresa S.L."
        company_nif = tenant_obj.nif if tenant_obj else "B00000000"

        invoice_data = _build_invoice_data(invoice, company_name, company_nif)
        pdf_bytes = generate_invoice_pdf(invoice_data, theme_config)
        file_name = f"Factura_{invoice_data['number']}.pdf"

        os.makedirs(UPLOAD_DIR, exist_ok=True)
        unique_name = f"{uuid_mod.uuid4().hex}.pdf"
        file_path = os.path.join(UPLOAD_DIR, unique_name)
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        async with AsyncSessionLocal() as session:
            doc = TenantDocument(
                tenant_id=tenant_id,
                uploaded_by=user_id,
                file_name=file_name,
                file_type="application/pdf",
                file_path=file_path,
                file_size=len(pdf_bytes),
                category="Facturas",
                status="ready",
            )
            session.add(doc)
            await session.commit()
    except Exception as e:
        logger.error("Error generando PDF de factura: %s", e)


# â”€â”€ Accounting commands â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


async def create_journal_entry(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    date,
    description: str,
    reference_id: str | None,
    lines: list[dict],
    invoice_id: UUID | None = None,
    payroll_id: UUID | None = None,
) -> JournalEntry:
    total_debit = sum(line["debit"] for line in lines)
    total_credit = sum(line["credit"] for line in lines)

    if abs(total_debit - total_credit) > 0.01:
        raise ValueError(
            f"El asiento está descuadrado: Debe ({total_debit}) != Haber ({total_credit})"
        )

    # Bloquear escritura si el periodo está cerrado
    from app.services.accounting import PeriodClosedError, is_date_locked
    _date_for_check = date.date() if hasattr(date, "date") and callable(getattr(date, "date")) else date
    locked, label = await is_date_locked(db, tenant_id, _date_for_check)
    if locked:
        raise PeriodClosedError(label or "?", target_date=_date_for_check if hasattr(_date_for_check, "isoformat") else None)

    new_entry = JournalEntry(
        tenant_id=tenant_id,
        date=date,
        description=description,
        reference_id=reference_id,
        invoice_id=invoice_id,
        payroll_id=payroll_id,
    )
    db.add(new_entry)
    await db.flush()

    for line_data in lines:
        new_line = JournalLine(
            tenant_id=tenant_id,
            entry_id=new_entry.id,
            account_code=line_data["account_code"],
            account_name=line_data.get("account_name"),
            debit=line_data["debit"],
            credit=line_data["credit"],
        )
        db.add(new_line)

    await db.commit()
    await db.refresh(new_entry)

    stmt = (
        select(JournalEntry)
        .where(JournalEntry.id == new_entry.id)
        .options(selectinload(JournalEntry.lines))
    )
    res = await db.execute(stmt)
    return res.scalar_one()


async def delete_journal_entry(
    db: AsyncSession, tenant_id: UUID, entry_id: UUID
) -> None:
    result = await db.execute(
        select(JournalEntry).where(
            JournalEntry.id == entry_id, JournalEntry.tenant_id == tenant_id
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise LookupError("Asiento no encontrado")

    # Bloquear borrado si el periodo está cerrado
    from app.services.accounting import PeriodClosedError, is_date_locked
    _date_for_check = entry.date.date() if hasattr(entry.date, "date") and callable(getattr(entry.date, "date")) else entry.date
    locked, label = await is_date_locked(db, tenant_id, _date_for_check)
    if locked:
        raise PeriodClosedError(label or "?", target_date=_date_for_check)

    await db.delete(entry)
    await db.commit()


async def create_fixed_asset(
    db: AsyncSession, tenant_id: UUID, data: dict
) -> FixedAsset:
    asset = FixedAsset(tenant_id=tenant_id, **data)
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


async def update_fixed_asset(
    db: AsyncSession, tenant_id: UUID, asset_id: UUID, data: dict
) -> FixedAsset:
    result = await db.execute(
        select(FixedAsset).where(
            FixedAsset.id == asset_id, FixedAsset.tenant_id == tenant_id
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise LookupError("Activo no encontrado")
    for field, value in data.items():
        setattr(asset, field, value)
    await db.commit()
    await db.refresh(asset)
    return asset


async def delete_fixed_asset(
    db: AsyncSession, tenant_id: UUID, asset_id: UUID
) -> None:
    result = await db.execute(
        select(FixedAsset).where(
            FixedAsset.id == asset_id, FixedAsset.tenant_id == tenant_id
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise LookupError("Activo no encontrado")
    await db.delete(asset)
    await db.commit()


# â”€â”€ Recurring commands â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


async def create_recurring(
    payload, tenant_id: UUID, db: AsyncSession
) -> RecurringInvoice:
    rec = RecurringInvoice(
        tenant_id=tenant_id,
        client_id=payload.client_id,
        name=payload.name,
        interval_type=payload.interval_type,
        next_run_date=payload.next_run_date,
        notes=payload.notes,
        terms=payload.terms,
        lines_json=[line.model_dump() for line in payload.lines],
    )
    db.add(rec)
    await db.commit()
    result = await db.execute(
        select(RecurringInvoice)
        .where(RecurringInvoice.id == rec.id)
        .options(joinedload(RecurringInvoice.client))
    )
    return result.unique().scalar_one()


async def update_recurring(
    rec_id: UUID,
    payload,
    tenant_id: UUID,
    db: AsyncSession,
) -> RecurringInvoice | None:
    """Returns updated record or None if not found."""
    result = await db.execute(
        select(RecurringInvoice).where(
            RecurringInvoice.id == rec_id,
            RecurringInvoice.tenant_id == tenant_id,
        )
    )
    rec = result.scalar_one_or_none()
    if not rec:
        return None

    data = payload.model_dump(exclude_unset=True)
    if "lines" in data:
        data["lines_json"] = data.pop("lines")
    for field, value in data.items():
        setattr(rec, field, value)
    await db.commit()

    result = await db.execute(
        select(RecurringInvoice)
        .where(RecurringInvoice.id == rec_id)
        .options(joinedload(RecurringInvoice.client))
    )
    return result.unique().scalar_one()


async def delete_recurring(
    rec_id: UUID, tenant_id: UUID, db: AsyncSession
) -> bool:
    """Returns False if not found."""
    result = await db.execute(
        select(RecurringInvoice).where(
            RecurringInvoice.id == rec_id,
            RecurringInvoice.tenant_id == tenant_id,
        )
    )
    rec = result.scalar_one_or_none()
    if not rec:
        return False
    await db.delete(rec)
    await db.commit()
    return True


async def run_recurring(
    rec_id: UUID, tenant_id: UUID, db: AsyncSession
) -> Invoice | None:
    """Genera una factura desde una plantilla recurrente. None si no existe."""
    import datetime as dt_module

    result = await db.execute(
        select(RecurringInvoice)
        .where(RecurringInvoice.id == rec_id, RecurringInvoice.tenant_id == tenant_id)
        .options(joinedload(RecurringInvoice.client))
    )
    rec = result.unique().scalar_one_or_none()
    if not rec:
        return None

    now = dt_module.datetime.now(dt_module.UTC)
    invoice_number = f"REC-{now.strftime('%Y%m%d%H%M%S')}"

    amount_base = 0.0
    tax_amount = 0.0
    for line in rec.lines_json or []:
        base = float(line.get("quantity", 1)) * float(line.get("unit_price", 0))
        tax = base * (float(line.get("tax_percentage", 21)) / 100)
        amount_base += base
        tax_amount += tax

    invoice = Invoice(
        tenant_id=tenant_id,
        client_id=rec.client_id,
        invoice_number=invoice_number,
        date=now,
        status="draft",
        invoice_type="issued",
        notes=rec.notes,
        terms=rec.terms,
        amount_base=round(amount_base, 2),
        tax_amount=round(tax_amount, 2),
        amount_total=round(amount_base + tax_amount, 2),
    )
    db.add(invoice)
    await db.flush()

    for line in rec.lines_json or []:
        base = float(line.get("quantity", 1)) * float(line.get("unit_price", 0))
        tax = base * (float(line.get("tax_percentage", 21)) / 100)
        inv_line = InvoiceLine(
            invoice_id=invoice.id,
            description=line.get("description", ""),
            quantity=line.get("quantity", 1),
            unit_price=line.get("unit_price", 0),
            discount_percentage=0,
            tax_percentage=line.get("tax_percentage", 21),
            total=round(base + tax, 2),
        )
        db.add(inv_line)

    interval_map = {"weekly": 7, "monthly": 30, "quarterly": 90, "yearly": 365}
    days = interval_map.get(rec.interval_type, 30)
    rec.last_run_date = now.date()
    rec.next_run_date = (now + dt_module.timedelta(days=days)).date()

    await db.commit()

    res = await db.execute(
        select(Invoice)
        .where(Invoice.id == invoice.id)
        .options(joinedload(Invoice.client), joinedload(Invoice.lines))
    )
    return res.unique().scalar_one()
