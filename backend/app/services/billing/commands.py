"""Billing commands â€” write operations (CQRS-lite).

All functions here produce side effects: INSERT/UPDATE/DELETE or file writes.
Read helpers are imported from queries.py to avoid duplication.
"""

import logging
import os
import uuid as uuid_mod
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.db.models.models import (
    FixedAsset,
    Invoice,
    InvoiceLine,
    JournalEntry,
    JournalLine,
    RecurringInvoice,
    Tenant,
    TenantDocument,
)
from app.services.billing.numbering import next_invoice_number
from app.services.billing.queries import (
    UPLOAD_DIR,
    _build_invoice_data,
    _load_invoice,
    compute_invoice_totals,
)
from app.services.state_machine import allowed_next_states, can_transition

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
    # Tipo de la factura que se crea. La unicidad del número solo aplica a las
    # que emitimos nosotros (issued/rectificativa); las recibidas llevan el
    # número del proveedor y quedan fuera de la guarda y del índice parcial.
    new_type = (payload_dict.get("invoice_type") or "issued")
    is_emitted = new_type in ("issued", "rectificativa")

    # 1) Validar líneas y calcular totales (Decimal) ANTES de consumir un número
    #    de serie. Si algo falla aquí (IVA inválido, total negativo), no se ha
    #    tocado el contador → sin huecos ni facturas huérfanas (RD 1619/2012).
    totals = compute_invoice_totals(lines_data)

    # 2) Número correlativo dentro de la MISMA transacción (advisory lock +
    #    FOR UPDATE en next_invoice_number; evita la carrera de la 1ª factura).
    if manual_number:
        # La numeración automática ya está protegida por el advisory lock de
        # next_invoice_number; el vector de duplicados que queda es el número
        # manual. Rechazamos uno ya emitido para este tenant (sin esto se han
        # llegado a ver dos facturas con el mismo número). Solo para facturas
        # emitidas: una recibida puede repetir el número del proveedor.
        if is_emitted:
            dup = await db.execute(
                select(Invoice.id)
                .where(
                    Invoice.tenant_id == tenant_id,
                    Invoice.invoice_number == manual_number,
                    Invoice.invoice_type.in_(("issued", "rectificativa")),
                )
                .limit(1)
            )
            if dup.scalar_one_or_none() is not None:
                raise ValueError(f"Ya existe una factura con el número {manual_number}.")
        invoice_number = manual_number
    else:
        invoice_number = await next_invoice_number(db, tenant_id, series=serie)

    # 3) Cabecera con los totales ya calculados. El id (UUID) está disponible al
    #    instanciar, por lo que las líneas lo referencian sin commit previo y
    #    todo (contador + cabecera + líneas + huella Verifactu) es un único commit.
    new_invoice = Invoice(
        tenant_id=tenant_id,
        client_id=client_id,
        invoice_number=invoice_number,
        amount_base=totals["amount_base"],
        tax_amount=totals["tax_amount"],
        amount_total=totals["amount_total"],
        **payload_dict,
    )
    db.add(new_invoice)
    # `Invoice.id` (default=uuid4) es un default de columna que SQLAlchemy aplica
    # en el flush, no al instanciar; hacemos flush para poblar el id y que las
    # líneas lo referencien. flush ≠ commit → sigue siendo atómico (un solo
    # commit al final; si algo falla, rollback deshace también el contador).
    await db.flush()

    for ld in totals["lines"]:
        db.add(
            InvoiceLine(
                invoice_id=new_invoice.id,
                product_id=ld.get("product_id"),
                description=ld.get("description"),
                quantity=ld["quantity"],
                unit_price=ld["unit_price"],
                discount_percentage=ld["discount_percentage"],
                tax_percentage=ld["tax_percentage"],
                total=ld["_line_total"],
            )
        )

    if lines_data and totals["amount_total"] == 0:
        logger.warning("Factura creada con importe 0 para cliente %s", client_id)

    # Verifactu: encadena la huella ANTES del commit → factura y huella atómicas.
    # En modo "no_remission" no hace nada.
    from app.services.billing.verifactu_chain import maybe_append_verifactu_record
    await maybe_append_verifactu_record(db, invoice=new_invoice)

    try:
        await db.commit()
    except IntegrityError as e:
        # Backstop del índice único parcial (tenant, número) para emitidas:
        # cubre la carrera concurrente que la guarda de aplicación no ve.
        await db.rollback()
        if "uq_invoices_tenant_number_emitted" in str(e.orig):
            raise ValueError(
                f"Ya existe una factura con el número {invoice_number}."
            ) from e
        raise

    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.client), joinedload(Invoice.lines))
        .where(Invoice.id == new_invoice.id)
    )
    return result.unique().scalar_one()


async def create_rectificativa(
    original_invoice_id: UUID,
    reason: str,
    tenant_id,
    db: AsyncSession,
    serie: str = "R",
):
    """Crea una factura rectificativa por anulación (RD 1619/2012 Art. 15).

    Emite una NUEVA factura que minora íntegramente a la original: mismas líneas
    con importes negados (sustitución total → deja la operación a cero). Queda
    vinculada a la original (`rectifies_invoice_id`) con su motivo, lleva su
    propia numeración correlativa (serie "R" por defecto) y su propio eslabón en
    la cadena Verifactu. Todo en un único commit atómico: si algo falla, el
    rollback deshace también el contador (sin huecos ni huérfanas).

    Lanza ValueError si la original no existe, si ya es una rectificativa, si ya
    tiene una rectificativa emitida, o si falta el motivo.
    """
    if not reason or not reason.strip():
        raise ValueError("La factura rectificativa requiere un motivo.")

    original = await _load_invoice(original_invoice_id, tenant_id, db)
    if original is None:
        raise ValueError("Factura original no encontrada")
    if (original.invoice_type or "").lower() == "rectificativa":
        raise ValueError("No se puede rectificar una factura rectificativa.")

    # Idempotencia: una factura solo se anula una vez. Evita dobles abonos.
    dup = await db.execute(
        select(Invoice.id)
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.rectifies_invoice_id == original.id,
        )
        .limit(1)
    )
    if dup.scalar_one_or_none() is not None:
        raise ValueError("Ya existe una factura rectificativa para esta factura.")

    # Líneas negadas → reutiliza la aritmética Decimal validada (allow_negative).
    neg_lines = [
        {
            "product_id": ln.product_id,
            "description": ln.description,
            "quantity": float(ln.quantity or 0),
            "unit_price": -float(ln.unit_price or 0),
            "discount_percentage": float(ln.discount_percentage or 0),
            "tax_percentage": float(ln.tax_percentage or 21),
        }
        for ln in original.lines
    ]
    totals = compute_invoice_totals(neg_lines, allow_negative=True)

    serie = (serie or "R").upper()[:10]
    invoice_number = await next_invoice_number(db, tenant_id, series=serie)

    rect = Invoice(
        tenant_id=tenant_id,
        client_id=original.client_id,
        invoice_number=invoice_number,
        date=datetime.now(UTC),
        status="pending",
        invoice_type="rectificativa",
        rectifies_invoice_id=original.id,
        rectification_reason=reason.strip(),
        notes=f"Factura rectificativa de {original.invoice_number}. Motivo: {reason.strip()}",
        amount_base=totals["amount_base"],
        tax_amount=totals["tax_amount"],
        amount_total=totals["amount_total"],
    )
    db.add(rect)
    await db.flush()  # poblar rect.id antes de las líneas (atómico, sin commit)

    for ld in totals["lines"]:
        db.add(
            InvoiceLine(
                invoice_id=rect.id,
                product_id=ld.get("product_id"),
                description=ld.get("description"),
                quantity=ld["quantity"],
                unit_price=ld["unit_price"],
                discount_percentage=ld["discount_percentage"],
                tax_percentage=ld["tax_percentage"],
                total=ld["_line_total"],
            )
        )

    # Verifactu: la rectificativa es un hecho con efectos fiscales → encadena su
    # propia huella ANTES del commit (atómico con la factura).
    from app.services.billing.verifactu_chain import maybe_append_verifactu_record
    await maybe_append_verifactu_record(db, invoice=rect)

    await db.commit()

    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.client), joinedload(Invoice.lines))
        .where(Invoice.id == rect.id)
    )
    return result.unique().scalar_one()


async def update_status(
    invoice_id: UUID,
    tenant_id,
    new_status: str,
    db: AsyncSession,
):
    """Cambia estado. Lanza ValueError si no existe o transición inválida."""
    allowed = {"draft", "pending", "sent", "paid", "cancelled"}
    if new_status not in allowed:
        raise ValueError(f"Estado no válido. Opciones: {allowed}")

    invoice = await _load_invoice(invoice_id, tenant_id, db)
    if not invoice:
        raise ValueError("Factura no encontrada")

    prev_status = invoice.status
    if new_status != prev_status and not can_transition("Invoice", prev_status, new_status):
        raise ValueError(
            f"Transición inválida: '{prev_status}' → '{new_status}'. "
            f"Permitidos: {allowed_next_states('Invoice', prev_status)}"
        )
    invoice.status = new_status
    await db.commit()
    await db.refresh(invoice)

    # Evento de negocio: al pasar a "paid" disparamos `invoice_paid` (trigger
    # documentado que antes nunca se emitía → las automatizaciones "factura
    # cobrada → …" no se ejecutaban). Best-effort: un fallo en los workflows no
    # debe revertir el cambio de estado.
    if new_status == "paid" and prev_status != "paid":
        try:
            from app.services.event_bus import emit_event
            await emit_event(
                db=db,
                tenant_id=tenant_id,
                user_id=None,
                event_name="invoice_paid",
                context={
                    "invoice_id": str(invoice.id),
                    "invoice_number": invoice.invoice_number,
                    "amount_total": float(invoice.amount_total or 0),
                },
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("No se pudo emitir invoice_paid: %s", e)

    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.client), joinedload(Invoice.lines))
        .where(Invoice.id == invoice_id)
    )
    return result.unique().scalar_one()


async def delete_invoice(invoice_id: UUID, tenant_id, db: AsyncSession) -> bool:
    """Borra una factura y, en cascada, sus asientos contables derivados.

    La FK ``journal_entries.invoice_id`` (sin ON DELETE) bloqueaba el borrado de
    una factura con asiento (típico en facturas recibidas) → 500. Aquí se borran
    primero los asientos vinculados (sus líneas caen por cascade ORM).

    Salvaguardas:
      - Si la factura tiene registro Verifactu, NO se borra (la cadena es
        inmutable/append-only) — se lanza ValueError con un mensaje claro.
      - Si algún asiento está en un periodo contable cerrado, tampoco — ValueError.
    """
    from app.db.models.billing import VerifactuRecord
    from app.services.accounting import is_date_locked

    invoice = await _load_invoice(invoice_id, tenant_id, db, with_joins=False)
    if not invoice:
        return False

    vf = await db.execute(
        select(VerifactuRecord.id).where(VerifactuRecord.invoice_id == invoice_id).limit(1)
    )
    if vf.scalar_one_or_none() is not None:
        raise ValueError(
            "No se puede borrar: la factura tiene un registro Verifactu (cadena inmutable)."
        )

    # N7: una factura EMITIDA ya numerada (pending/sent/paid) no se borra: rompería
    # la numeración correlativa (RD 1619/2012 Art. 6.1) y el contador no retrocede.
    # Los borradores sí (nunca se emitieron); las recibidas y las demo también.
    # Para anular una factura emitida, se emite una factura rectificativa.
    if (
        invoice.invoice_type == "issued"
        and not invoice.is_demo
        and (invoice.status or "draft") != "draft"
    ):
        raise ValueError(
            f"No se puede borrar una factura emitida (estado '{invoice.status}'): rompería "
            "la numeración correlativa. Para anularla, emite una factura rectificativa."
        )

    entries_res = await db.execute(
        select(JournalEntry).where(
            JournalEntry.invoice_id == invoice_id,
            JournalEntry.tenant_id == tenant_id,
        )
    )
    entries = list(entries_res.scalars().all())
    for entry in entries:
        _d = entry.date.date() if hasattr(entry.date, "date") and callable(entry.date.date) else entry.date
        locked, label = await is_date_locked(db, tenant_id, _d)
        if locked:
            raise ValueError(
                f"No se puede borrar: el asiento contable está en un periodo cerrado ({label or '?'})."
            )
    for entry in entries:
        await db.delete(entry)

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
                # Procedencia: este PDF es un artefacto que genera el ERP, no un
                # documento externo. Marcarlo como "generated" + enlazarlo a su
                # factura evita que una asimilación documento→ERP lo trate como
                # una factura nueva (sería un duplicado).
                source="generated",
                entity_type="invoice",
                entity_id=invoice.id,
            )
            session.add(doc)
            await session.flush()
            # Enlace inverso: la factura conoce su documento (columna document_id
            # que hasta ahora quedaba sin rellenar). Así el reflejo es navegable
            # en ambos sentidos.
            await session.execute(
                update(Invoice)
                .where(Invoice.id == invoice.id, Invoice.tenant_id == tenant_id)
                .values(document_id=doc.id)
            )
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
    # N6: cuadre en Decimal (no float) para no enmascarar descuadres reales. Se
    # tolera ≤1 céntimo: al redondear base/IVA/total de una factura por separado
    # puede quedar un descuadre legítimo de 0,01 € (no es error binario). Un cuadre
    # EXACTO exigiría una línea de ajuste por redondeo (669/769) — fuera de alcance.
    total_debit = sum((Decimal(str(line["debit"])) for line in lines), Decimal("0"))
    total_credit = sum((Decimal(str(line["credit"])) for line in lines), Decimal("0"))

    if abs(total_debit - total_credit) > Decimal("0.01"):
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

    # Totales con Decimal (mismo cálculo canónico que create_invoice): respeta
    # descuentos y valida el IVA, evitando el arrastre de redondeo del float.
    totals = compute_invoice_totals(rec.lines_json or [])

    invoice = Invoice(
        tenant_id=tenant_id,
        client_id=rec.client_id,
        invoice_number=invoice_number,
        date=now,
        status="draft",
        invoice_type="issued",
        notes=rec.notes,
        terms=rec.terms,
        amount_base=totals["amount_base"],
        tax_amount=totals["tax_amount"],
        amount_total=totals["amount_total"],
    )
    db.add(invoice)
    await db.flush()

    for ld in totals["lines"]:
        db.add(
            InvoiceLine(
                invoice_id=invoice.id,
                product_id=ld.get("product_id"),
                description=ld.get("description", ""),
                quantity=ld["quantity"],
                unit_price=ld["unit_price"],
                discount_percentage=ld["discount_percentage"],
                tax_percentage=ld["tax_percentage"],
                total=ld["_line_total"],
            )
        )

    # Verifactu: encadena la huella ANTES del commit (igual que create_invoice).
    # Sin esto, una recurrente en modo Verifactu quedaba fuera de la cadena
    # append-only (hueco). No-op si el tenant está en modo no_remission.
    from app.services.billing.verifactu_chain import maybe_append_verifactu_record
    await maybe_append_verifactu_record(db, invoice=invoice)

    # Próxima ejecución respetando meses/años reales (fin de mes, bisiestos) en
    # vez de sumar días fijos (30/90/365) que acumulan deriva. Aritmética de
    # meses con `calendar` para no añadir una dependencia (dateutil) sin stubs.
    import calendar as _cal

    def _add_months(d: dt_module.date, months: int) -> dt_module.date:
        m = d.month - 1 + months
        y = d.year + m // 12
        mon = m % 12 + 1
        return d.replace(year=y, month=mon, day=min(d.day, _cal.monthrange(y, mon)[1]))

    today = now.date()
    if rec.interval_type == "weekly":
        next_date = today + dt_module.timedelta(weeks=1)
    elif rec.interval_type == "quarterly":
        next_date = _add_months(today, 3)
    elif rec.interval_type == "yearly":
        next_date = _add_months(today, 12)
    else:  # monthly (default)
        next_date = _add_months(today, 1)
    rec.last_run_date = today
    rec.next_run_date = next_date

    await db.commit()

    res = await db.execute(
        select(Invoice)
        .where(Invoice.id == invoice.id)
        .options(joinedload(Invoice.client), joinedload(Invoice.lines))
    )
    return res.unique().scalar_one()
