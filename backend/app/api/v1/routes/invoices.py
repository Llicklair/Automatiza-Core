import logging
import os
import uuid as uuid_mod
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.v1.routes.templates import get_default_theme
from app.api.v1.schemas.erp import (
    InvoiceCreate,
    InvoiceResponse,
    InvoiceStatusUpdate,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import (
    Invoice,
    InvoiceLine,
    InvoiceSeries,
    Tenant,
    TenantDocument,
    User,
)
from app.middleware.rate_limit import limiter
from app.services.event_bus import emit_event
from app.services.pdf_service import (
    generate_invoice_pdf,
    generate_rectificative_invoice_pdf,
    generate_retention_invoice_pdf,
)

logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "uploads")
)


@router.get("/invoices", response_model=list[InvoiceResponse], tags=["erp"])
@limiter.limit("30/minute")
async def list_invoices(
    request: Request,
    skip: int = 0,
    limit: int = Query(default=50, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Invoice)
        .options(
            joinedload(Invoice.client),
            joinedload(Invoice.lines),
        )
        .where(Invoice.tenant_id == current_user.tenant_id)
        .order_by(desc(Invoice.created_at))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return result.unique().scalars().all()


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse, tags=["erp"])
@limiter.limit("30/minute")
async def get_invoice(
    request: Request,
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve el detalle de una factura (con cliente y líneas)."""
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.client), joinedload(Invoice.lines))
        .where(Invoice.id == invoice_id, Invoice.tenant_id == current_user.tenant_id)
    )
    invoice = result.unique().scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return invoice


@router.patch("/invoices/{invoice_id}/status", response_model=InvoiceResponse, tags=["erp"])
@limiter.limit("30/minute")
async def update_invoice_status(
    request: Request,
    invoice_id: UUID,
    payload: InvoiceStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cambia el estado de una factura: draft → pending → paid | cancelled."""
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.client), joinedload(Invoice.lines))
        .where(Invoice.id == invoice_id, Invoice.tenant_id == current_user.tenant_id)
    )
    invoice = result.unique().scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    allowed = {"draft", "pending", "paid", "cancelled"}
    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail=f"Estado no válido. Opciones: {allowed}")
    invoice.status = payload.status
    await db.commit()
    await db.refresh(invoice)
    result2 = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.client), joinedload(Invoice.lines))
        .where(Invoice.id == invoice_id)
    )
    return result2.unique().scalar_one()


@router.delete("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["erp"])
@limiter.limit("30/minute")
async def delete_invoice(
    request: Request,
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.tenant_id == current_user.tenant_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    await db.delete(invoice)
    await db.commit()


@router.post(
    "/clients/{client_id}/invoices",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["erp"],
)
@limiter.limit("30/minute")
async def create_invoice(
    request: Request,
    client_id: UUID,
    payload: InvoiceCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Descomponemos el payload
    payload_dict = payload.model_dump()
    lines_data = payload_dict.pop("lines", [])

    # Ignorar posibles campos totalizadores de frontend
    payload_dict.pop("amount_base", None)
    payload_dict.pop("tax_amount", None)
    payload_dict.pop("amount_total", None)

    # 0. Generar número de factura correlativo con SELECT FOR UPDATE
    manual_number = payload_dict.pop("invoice_number", None)
    serie = payload_dict.pop("serie", "F") or "F"
    serie = serie.upper()[:10]

    if manual_number:
        invoice_number = manual_number
    else:
        invoice_year = datetime.now(timezone.utc).year

        series_result = await db.execute(
            select(InvoiceSeries)
            .where(
                InvoiceSeries.tenant_id == current_user.tenant_id,
                InvoiceSeries.serie == serie,
                InvoiceSeries.year == invoice_year,
            )
            .with_for_update()
        )
        series_row = series_result.scalar_one_or_none()

        if series_row is None:
            series_row = InvoiceSeries(
                tenant_id=current_user.tenant_id,
                serie=serie,
                year=invoice_year,
                last_number=0,
                prefix=serie,
            )
            db.add(series_row)
            await db.flush()

        series_row.last_number += 1
        invoice_number = f"{series_row.prefix}{invoice_year}-{series_row.last_number:04d}"

    # 1. Crear el padre (Invoice) con bases en cero
    new_invoice = Invoice(
        tenant_id=current_user.tenant_id,
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

    # 2. Insertar las InvoiceLine y calcular sumatorios
    total_base = 0.0
    total_tax = 0.0

    for line_data in lines_data:
        # Recuperamos datos de base
        qty = float(line_data.get("quantity", 1))
        uprice = float(line_data.get("unit_price", 0))
        discount_perc = float(line_data.get("discount_percentage", 0))
        tax_perc = float(line_data.get("tax_percentage", 21))

        # Validar tipo de IVA (valores legales en España)
        VALID_IVA = {0.0, 4.0, 10.0, 21.0}
        if tax_perc not in VALID_IVA:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de IVA inválido: {tax_perc}%. Los valores permitidos son: 0%, 4%, 10%, 21%.",
            )

        # Calcular línea individual
        line_base = qty * uprice
        if discount_perc > 0:
            line_base -= line_base * (discount_perc / 100)

        line_tax = line_base * (tax_perc / 100)
        line_total = line_base + line_tax

        # Acumular globales
        total_base += line_base
        total_tax += line_tax

        # Guardar línea
        inv_line = InvoiceLine(
            invoice_id=new_invoice.id,
            product_id=line_data.get("product_id"),
            description=line_data.get("description"),
            quantity=qty,
            unit_price=uprice,
            discount_percentage=discount_perc,
            tax_percentage=tax_perc,
            total=line_total,
        )
        db.add(inv_line)

    # 3. Actualizar el padre con los cálculos sumados
    new_invoice.amount_base = round(total_base, 2)
    new_invoice.tax_amount = round(total_tax, 2)
    new_invoice.amount_total = round(total_base + total_tax, 2)

    # Validaciones post-cálculo
    if new_invoice.amount_total < 0:
        await db.rollback()
        raise HTTPException(
            status_code=400, detail="El importe total de la factura no puede ser negativo."
        )
    if lines_data and new_invoice.amount_total == 0:
        logger.warning("Factura creada con importe 0 para cliente %s", client_id)

    await db.commit()

    # 4. Refrescar Invoice para devolver con joins
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.client), joinedload(Invoice.lines))
        .where(Invoice.id == new_invoice.id)
    )
    final_invoice = result.unique().scalar_one()

    # 5. Generar PDF y guardarlo en TenantDocument (en background)
    background_tasks.add_task(
        _generate_and_save_invoice_pdf,
        invoice=final_invoice,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )

    # 6. Emitir evento para disparar automatizaciones event_based
    await emit_event(
        db=db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        event_name="invoice_created",
        context={
            "invoice_id": str(final_invoice.id),
            "invoice_number": final_invoice.invoice_number,
            "amount_total": float(final_invoice.amount_total or 0),
            "client_name": final_invoice.client.name if final_invoice.client else None,
            "status": final_invoice.status,
        },
    )

    return final_invoice


async def _generate_and_save_invoice_pdf(invoice, tenant_id, user_id):
    """Genera el PDF de la factura y lo registra como TenantDocument."""
    from app.db.base import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as session:
            tenant_obj = await session.get(Tenant, tenant_id)
            theme_config = await get_default_theme(tenant_id, "invoice", session)

        company_name = tenant_obj.name if tenant_obj else "Mi Empresa S.L."
        company_nif = tenant_obj.nif if tenant_obj else "B00000000"

        invoice_data = {
            "number": invoice.invoice_number or f"F-{str(invoice.id)[:8].upper()}",
            "date": invoice.date.isoformat() if invoice.date else "",
            "amount_base": float(invoice.amount_base or 0),
            "tax_amount": float(invoice.tax_amount or 0),
            "amount_total": float(invoice.amount_total or 0),
            "client": {
                "name": invoice.client.name if invoice.client else "Cliente",
                "nif": invoice.client.nif if invoice.client else "",
                "email": invoice.client.email if invoice.client else "",
                "address": invoice.client.address if invoice.client else "",
            },
            "company": {
                "name": company_name,
                "nif": company_nif,
                "address": "Calle Principal, 1 · Madrid",
                "phone": "",
            },
            "lines": [
                {
                    "description": line.description or "",
                    "quantity": float(line.quantity or 1),
                    "unit_price": float(line.unit_price or 0),
                    "tax_percentage": float(line.tax_percentage or 21),
                    "total": float(line.total or 0),
                }
                for line in (invoice.lines or [])
            ],
            "notes": invoice.notes or "",
            "payment_terms": invoice.terms or "",
        }

        pdf_bytes = generate_invoice_pdf(invoice_data, theme_config)
        file_name = f"Factura_{invoice_data['number']}.pdf"

        # Guardar en disco
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        unique_name = f"{uuid_mod.uuid4().hex}.pdf"
        file_path = os.path.join(UPLOAD_DIR, unique_name)
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        # Registrar en TenantDocument
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


@router.get("/invoices/{invoice_id}/pdf", tags=["erp"])
@limiter.limit("30/minute")
async def download_invoice_pdf(
    request: Request,
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Descarga el PDF de una factura específica generándolo al vuelo."""
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.client), joinedload(Invoice.lines))
        .where(Invoice.id == invoice_id, Invoice.tenant_id == current_user.tenant_id)
    )
    invoice = result.unique().scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant_obj = tenant_result.scalar_one_or_none()
    company_name = tenant_obj.name if tenant_obj else "Mi Empresa S.L."
    company_nif = tenant_obj.nif if tenant_obj else "B00000000"
    theme_config = await get_default_theme(current_user.tenant_id, "invoice", db)
    invoice_data = {
        "number": invoice.invoice_number or f"F-{str(invoice.id)[:8].upper()}",
        "date": invoice.date.isoformat() if invoice.date else "",
        "amount_base": float(invoice.amount_base or 0),
        "tax_amount": float(invoice.tax_amount or 0),
        "amount_total": float(invoice.amount_total or 0),
        "client": {
            "name": invoice.client.name if invoice.client else "Cliente",
            "nif": invoice.client.nif if invoice.client else "",
            "email": invoice.client.email if invoice.client else "",
            "address": invoice.client.address if invoice.client else "",
        },
        "company": {
            "name": company_name,
            "nif": company_nif,
            "address": "Calle Principal, 1 · Madrid",
            "phone": "",
        },
        "lines": [
            {
                "description": line.description or "",
                "quantity": float(line.quantity or 1),
                "unit_price": float(line.unit_price or 0),
                "tax_percentage": float(line.tax_percentage or 21),
                "total": float(line.total or 0),
            }
            for line in (invoice.lines or [])
        ],
        "notes": invoice.notes or "",
        "payment_terms": invoice.terms or "",
    }

    pdf_bytes = generate_invoice_pdf(invoice_data, theme_config)
    file_name = f"Factura_{invoice_data['number']}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.get("/invoices/{invoice_id}/rectificative-pdf", tags=["erp"])
@limiter.limit("30/minute")
async def download_rectificative_invoice_pdf(
    request: Request,
    invoice_id: UUID,
    reason: str = Query(default="Corrección de importes", description="Motivo de rectificación"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera PDF de factura rectificativa referenciando la factura original."""
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.client), joinedload(Invoice.lines))
        .where(Invoice.id == invoice_id, Invoice.tenant_id == current_user.tenant_id)
    )
    invoice = result.unique().scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant_obj = tenant_result.scalar_one_or_none()
    company_name = tenant_obj.name if tenant_obj else "Mi Empresa S.L."
    company_nif = tenant_obj.nif if tenant_obj else "B00000000"
    theme_config = await get_default_theme(current_user.tenant_id, "invoice", db)

    # Build rectificative data — by default zeroes out the original (full credit note)
    orig_base = float(invoice.amount_base or 0)
    orig_tax = float(invoice.tax_amount or 0)
    orig_total = float(invoice.amount_total or 0)

    corrected_lines = []
    for line in invoice.lines or []:
        corrected_lines.append(
            {
                "description": line.description or "",
                "original_amount": float(line.total or 0),
                "corrected_amount": 0.0,
            }
        )

    data = {
        "number": f"FR-{(invoice.invoice_number or str(invoice.id)[:8]).upper()}",
        "date": datetime.now(timezone.utc).isoformat(),
        "original_invoice": {
            "number": invoice.invoice_number or str(invoice.id)[:8],
            "date": invoice.date.isoformat() if invoice.date else "",
            "amount_base": orig_base,
            "tax_amount": orig_tax,
            "amount_total": orig_total,
        },
        "reason": reason,
        "corrected_lines": corrected_lines,
        "corrected_base": 0.0,
        "corrected_tax": 0.0,
        "corrected_total": 0.0,
        "company": {"name": company_name, "nif": company_nif, "address": "", "phone": ""},
        "client": {
            "name": invoice.client.name if invoice.client else "Cliente",
            "nif": invoice.client.nif if invoice.client else "",
            "email": invoice.client.email if invoice.client else "",
            "address": invoice.client.address if invoice.client else "",
        },
    }

    pdf_bytes = generate_rectificative_invoice_pdf(data, theme_config)
    file_name = f"Rectificativa_{data['number']}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.get("/invoices/{invoice_id}/retention-pdf", tags=["erp"])
@limiter.limit("30/minute")
async def download_retention_invoice_pdf(
    request: Request,
    invoice_id: UUID,
    retention_pct: float = Query(default=15.0, description="Porcentaje de retención IRPF"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera PDF de factura con retención IRPF."""
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.client), joinedload(Invoice.lines))
        .where(Invoice.id == invoice_id, Invoice.tenant_id == current_user.tenant_id)
    )
    invoice = result.unique().scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant_obj = tenant_result.scalar_one_or_none()
    company_name = tenant_obj.name if tenant_obj else "Mi Empresa S.L."
    company_nif = tenant_obj.nif if tenant_obj else "B00000000"
    theme_config = await get_default_theme(current_user.tenant_id, "invoice", db)

    base = float(invoice.amount_base or 0)
    tax = float(invoice.tax_amount or 0)
    retention_amount = round(base * retention_pct / 100, 2)

    data = {
        "number": invoice.invoice_number or f"F-{str(invoice.id)[:8].upper()}",
        "date": invoice.date.isoformat() if invoice.date else "",
        "amount_base": base,
        "tax_amount": tax,
        "amount_total": float(invoice.amount_total or 0),
        "retention_percentage": retention_pct,
        "retention_amount": retention_amount,
        "company": {"name": company_name, "nif": company_nif, "address": "", "phone": ""},
        "client": {
            "name": invoice.client.name if invoice.client else "Cliente",
            "nif": invoice.client.nif if invoice.client else "",
            "email": invoice.client.email if invoice.client else "",
            "address": invoice.client.address if invoice.client else "",
        },
        "lines": [
            {
                "description": line.description or "",
                "quantity": float(line.quantity or 1),
                "unit_price": float(line.unit_price or 0),
                "tax_percentage": float(line.tax_percentage or 21),
                "total": float(line.total or 0),
            }
            for line in (invoice.lines or [])
        ],
        "notes": invoice.notes or "",
        "payment_terms": invoice.terms or "",
    }

    pdf_bytes = generate_retention_invoice_pdf(data, theme_config)
    file_name = f"Factura_Retencion_{data['number']}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
