"""Rutas para facturas — thin controller."""

import logging
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Request, UploadFile, status
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


@router.post("/invoices/scan", status_code=status.HTTP_200_OK, tags=["erp"])
@limiter.limit("10/minute")
async def scan_invoice(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """OCR + IA sobre una factura recibida (imagen o PDF).

    Devuelve un borrador estructurado con emisor, líneas, IVA, vencimiento y
    avisos de incoherencia. NO crea nada en BD — el frontend confirma con
    POST /clients/{client_id}/invoices tras revisar/editar.

    Optimización F2.5 (aprendizaje por proveedor):
      1. Cache por hash → 0 tokens si el mismo PDF ya se escaneó.
      2. Few-shot del NIF → extracción más precisa en proveedores recurrentes.
      3. Overrides aprendidos → aplica correcciones del usuario.
    """
    from app.services.ocr import InvoiceExtractionError, extract_invoice_data
    from app.services.ocr.supplier_learning import (
        apply_template_overrides,
        build_few_shot_block,
        file_sha256,
        get_template,
        lookup_cached,
        record_extraction,
        save_to_cache,
    )

    content = await file.read()
    mime = file.content_type or "image/jpeg"

    file_hash = file_sha256(content)
    cached = await lookup_cached(db, current_user.tenant_id, file_hash)
    if cached is not None:
        logger.info("scan_invoice cache hit hash=%s", file_hash[:12])
        return cached

    try:
        data = await extract_invoice_data(
            content,
            mime,
            few_shot_hint=None,  # se completa abajo si hay template
            tenant_id=current_user.tenant_id,
            db=db,
        )
    except InvoiceExtractionError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Fallo procesando factura recibida")
        raise HTTPException(status_code=500, detail=f"Error procesando factura: {e}")

    payload = data.to_dict()
    nif = (payload.get("emisor") or {}).get("nif")

    if nif:
        template = await get_template(db, current_user.tenant_id, nif)
        if template is not None:
            # Re-llamamos con few-shot SÓLO si la confianza es baja y hay template
            if (payload.get("confidence") or 0) < 0.85:
                hint = build_few_shot_block(template)
                if hint:
                    try:
                        data = await extract_invoice_data(
                            content, mime, few_shot_hint=hint,
                            tenant_id=current_user.tenant_id, db=db,
                        )
                        payload = data.to_dict()
                    except Exception as e:
                        logger.warning("Re-extracción con few-shot falló: %s", e)
            payload = apply_template_overrides(payload, template)

        await record_extraction(db, current_user.tenant_id, payload)

    await save_to_cache(
        db,
        current_user.tenant_id,
        file_hash=file_hash,
        file_size=len(content),
        mime_type=mime,
        extracted_data=payload,
    )
    return payload


@router.post("/invoices/scan/learn", status_code=status.HTTP_200_OK, tags=["erp"])
@limiter.limit("30/minute")
async def learn_scan_correction(
    request: Request,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Guarda los overrides aprendidos cuando el usuario corrige una
    extracción del escáner.

    Body: {"supplier_nif": str, "original": dict, "corrected": dict}.
    Devuelve el diff de overrides persistidos.
    """
    from app.services.ocr.supplier_learning import save_correction

    nif = (payload or {}).get("supplier_nif")
    original = (payload or {}).get("original") or {}
    corrected = (payload or {}).get("corrected") or {}
    if not nif:
        raise HTTPException(status_code=422, detail="supplier_nif requerido.")

    diff = await save_correction(
        db, current_user.tenant_id, nif, original=original, corrected=corrected
    )
    return {"saved": bool(diff), "overrides": diff}


@router.post("/invoices/scan-batch", status_code=status.HTTP_200_OK, tags=["erp"])
@limiter.limit("5/minute")
async def scan_invoices_batch(
    request: Request,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """OCR + IA sobre VARIAS facturas recibidas a la vez.

    Por cada fichero: cache por hash → extracción → aprendizaje por proveedor.
    Un fallo en un fichero NO tumba el lote (se devuelve su `error`). NO crea
    nada en BD; el frontend revisa y confirma con POST /invoices/import.
    """
    from app.services.ocr import InvoiceExtractionError, extract_invoice_data
    from app.services.ocr.supplier_learning import (
        apply_template_overrides,
        file_sha256,
        get_template,
        lookup_cached,
        record_extraction,
        save_to_cache,
    )

    if len(files) > 20:
        raise HTTPException(status_code=422, detail="Máximo 20 facturas por lote.")

    results: list[dict] = []
    for f in files:
        try:
            content = await f.read()
            mime = f.content_type or "image/jpeg"
            file_hash = file_sha256(content)

            cached = await lookup_cached(db, current_user.tenant_id, file_hash)
            if cached is not None:
                results.append({"filename": f.filename, "extracted": cached, "error": None})
                continue

            data = await extract_invoice_data(
                content, mime, few_shot_hint=None,
                tenant_id=current_user.tenant_id, db=db,
            )
            payload = data.to_dict()
            nif = (payload.get("emisor") or {}).get("nif")
            if nif:
                template = await get_template(db, current_user.tenant_id, nif)
                if template is not None:
                    payload = apply_template_overrides(payload, template)
                await record_extraction(db, current_user.tenant_id, payload)
            await save_to_cache(
                db,
                current_user.tenant_id,
                file_hash=file_hash,
                file_size=len(content),
                mime_type=mime,
                extracted_data=payload,
            )
            results.append({"filename": f.filename, "extracted": payload, "error": None})
        except InvoiceExtractionError as e:
            results.append({"filename": f.filename, "extracted": None, "error": str(e)})
        except Exception as e:  # noqa: BLE001 — aislar fallos por fichero
            logger.exception("Fallo procesando factura del lote: %s", f.filename)
            results.append({"filename": f.filename, "extracted": None, "error": f"Error: {e}"})

    return {"results": results}


@router.post("/invoices/import", status_code=status.HTTP_200_OK, tags=["erp"])
@limiter.limit("10/minute")
async def import_invoices(
    request: Request,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Integra en el ERP facturas de COMPRA ya revisadas por el usuario.

    Body: {"drafts": [{emisor, invoice_number, issue_date, due_date, lines[],
    amount_base, tax_amount, amount_total, apply_stock: bool}, ...]}.

    Por cada borrador: crea proveedor si falta, crea la factura recibida +
    líneas, genera el asiento de compra y (si apply_stock) suma stock SOLO de
    las líneas que casan con el catálogo. Todo idempotente por referencia.
    """
    from app.services.billing.invoice_import import import_received_invoices

    drafts = (payload or {}).get("drafts")
    if not isinstance(drafts, list) or not drafts:
        raise HTTPException(status_code=422, detail="Se requiere 'drafts' (lista no vacía).")

    results = await import_received_invoices(
        db, current_user.tenant_id, drafts, current_user.id
    )
    # 'created' = facturas realmente nuevas. Los duplicados se devuelven con
    # ok=True + skipped=True (idempotencia), pero NO cuentan como creadas.
    created = sum(1 for r in results if r.get("ok") and not r.get("skipped"))
    skipped = sum(1 for r in results if r.get("skipped"))
    return {
        "created": created,
        "skipped": skipped,
        "total": len(results),
        "results": results,
    }


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
    try:
        deleted = await svc.delete_invoice(invoice_id, current_user.tenant_id, db)
    except ValueError as e:
        # Verifactu inmutable o periodo contable cerrado → 409 (conflicto), no 500.
        raise HTTPException(status_code=409, detail=str(e))
    if not deleted:
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


@router.post(
    "/invoices/{invoice_id}/rectificativa",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["erp"],
)
@limiter.limit("30/minute")
async def create_rectificativa(
    request: Request,
    invoice_id: UUID,
    payload: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Emite una factura rectificativa por anulación de la factura `invoice_id`.

    Body: {"reason": str, "serie": str?}. Crea una nueva factura que minora la
    original con importes negativos (RD 1619/2012 Art. 15), su numeración propia
    y su eslabón en la cadena Verifactu.
    """
    reason = (payload or {}).get("reason") or ""
    serie = (payload or {}).get("serie") or "R"
    try:
        rect = await svc.create_rectificativa(
            invoice_id, reason, current_user.tenant_id, db, serie=serie
        )
    except ValueError as e:
        code = 404 if "no encontrada" in str(e) else 400
        raise HTTPException(status_code=code, detail=str(e))

    background_tasks.add_task(
        svc.generate_and_save_invoice_pdf,
        invoice=rect,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )
    return rect


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
