"""Rutas para facturas — thin controller."""

import logging
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.erp import InvoiceCreate, InvoiceResponse, InvoiceStatusUpdate
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.auth import Tenant
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.billing import invoice as svc
from app.services.billing.facturae import generate_facturae_xml, mark_verifactu_sent
from app.services.event_bus import emit_event

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/invoices", response_model=list[InvoiceResponse], tags=["erp"])
@limiter.limit("30/minute")
async def list_invoices(
    request: Request,
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_invoices(current_user.tenant_id, db, skip, limit)


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse, tags=["erp"])
@limiter.limit("30/minute")
async def get_invoice(
    request: Request,
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = await svc.get_invoice(invoice_id, current_user.tenant_id, db)
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
    try:
        return await svc.update_status(invoice_id, current_user.tenant_id, payload.status, db)
    except ValueError as e:
        code = 404 if "no encontrada" in str(e) else 400
        raise HTTPException(status_code=code, detail=str(e))


@router.delete("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["erp"])
@limiter.limit("30/minute")
async def delete_invoice(
    request: Request,
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not await svc.delete_invoice(invoice_id, current_user.tenant_id, db):
        raise HTTPException(status_code=404, detail="Factura no encontrada")


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
    payload_dict = payload.model_dump()
    lines_data = payload_dict.pop("lines", [])

    try:
        final_invoice = await svc.create_invoice(
            client_id,
            payload_dict,
            lines_data,
            current_user.tenant_id,
            current_user.id,
            db,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    background_tasks.add_task(
        svc.generate_and_save_invoice_pdf,
        invoice=final_invoice,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )

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


@router.get("/invoices/{invoice_id}/pdf", tags=["erp"])
@limiter.limit("30/minute")
async def download_invoice_pdf(
    request: Request,
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        pdf_bytes, file_name = await svc.build_invoice_pdf(
            invoice_id,
            current_user.tenant_id,
            db,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
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
    try:
        pdf_bytes, file_name = await svc.build_rectificative_pdf(
            invoice_id,
            current_user.tenant_id,
            reason,
            db,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
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
    try:
        pdf_bytes, file_name = await svc.build_retention_pdf(
            invoice_id,
            current_user.tenant_id,
            retention_pct,
            db,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.get("/invoices/{invoice_id}/facturae", tags=["erp"])
@limiter.limit("20/minute")
async def download_facturae(
    request: Request,
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        xml_bytes, file_name = await generate_facturae_xml(invoice_id, current_user.tenant_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Auto-sign if tenant has a certificate
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    if tenant and tenant.cert_path and Path(tenant.cert_path).exists():
        try:
            from app.services.billing.xades_signer import sign_xml
            xml_bytes = sign_xml(xml_bytes, tenant.cert_path, tenant.cert_password or "")
        except Exception as exc:
            logger.warning("XAdES signing failed, returning unsigned XML: %s", exc)

    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.post("/invoices/{invoice_id}/verifactu-send", tags=["erp"])
@limiter.limit("10/minute")
async def send_to_verifactu(
    request: Request,
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await mark_verifactu_sent(invoice_id, current_user.tenant_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
