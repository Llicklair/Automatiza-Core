"""
Scanner / Gatekeeper — Endpoints para escáner móvil de almacén.

- POST /scanner/generate-qr   — Genera QR con token de corta vida (desktop → móvil)
- GET  /scanner/whoami         — Verifica token de scanner y devuelve info
- POST /scanner/scan-product   — Escanea producto por SKU/barcode, devuelve info + stock
- POST /scanner/stock-entry    — Registra entrada de stock
- POST /scanner/stock-exit     — Registra salida de stock
- POST /scanner/confirm-delivery — Confirma recepción de albarán
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.scanner import (
    ConfirmDeliveryRequest,
    GenerateQRRequest,
    ScanProductRequest,
    StockMovementRequest,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.middleware.rate_limit import limiter
from app.middleware.scanner_auth import create_scanner_token, get_scanner_user
from app.services.documents import scanner as svc

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Desktop-side: genera token para el móvil ────────────────────────────────


@router.post("/generate-qr")
@limiter.limit("10/minute")
async def generate_qr_token(
    request: Request,
    payload: GenerateQRRequest,
    current_user=Depends(get_current_user),
):
    """Genera un token JWT de corta vida para que un móvil escanee el QR.
    Solo accesible por usuarios autenticados desde el desktop."""
    token_data = create_scanner_token(
        tenant_id=str(current_user.tenant_id),
        user_id=str(current_user.id),
        device_name=payload.device_name,
    )
    return token_data


# ── Scanner-side: endpoints accesibles con token de scanner ─────────────────


@router.get("/whoami")
async def scanner_whoami(scanner=Depends(get_scanner_user)):
    """Verifica que el token de scanner es válido y devuelve info."""
    return {
        "status": "authenticated",
        "tenant_id": scanner["tenant_id"],
        "device": scanner.get("device", "unknown"),
        "scope": scanner.get("scope", ""),
    }


@router.post("/scan-product")
@limiter.limit("60/minute")
async def scan_product(
    request: Request,
    payload: ScanProductRequest,
    scanner=Depends(get_scanner_user),
    db: AsyncSession = Depends(get_db),
):
    """Busca un producto por SKU y devuelve info + stock actual."""
    try:
        return await svc.scan_product(db, UUID(scanner["tenant_id"]), payload.sku)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/stock-entry")
@limiter.limit("30/minute")
async def stock_entry(
    request: Request,
    payload: StockMovementRequest,
    scanner=Depends(get_scanner_user),
    db: AsyncSession = Depends(get_db),
):
    """Registra entrada de stock desde el escáner móvil."""
    try:
        return await svc.record_movement(
            db,
            UUID(scanner["tenant_id"]),
            payload.sku,
            payload.quantity,
            payload.notes,
            "entrada",
            scanner.get("device", "mobile"),
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/stock-exit")
@limiter.limit("30/minute")
async def stock_exit(
    request: Request,
    payload: StockMovementRequest,
    scanner=Depends(get_scanner_user),
    db: AsyncSession = Depends(get_db),
):
    """Registra salida de stock desde el escáner móvil."""
    try:
        return await svc.record_movement(
            db,
            UUID(scanner["tenant_id"]),
            payload.sku,
            payload.quantity,
            payload.notes,
            "salida",
            scanner.get("device", "mobile"),
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/confirm-delivery")
@limiter.limit("10/minute")
async def confirm_delivery(
    request: Request,
    payload: ConfirmDeliveryRequest,
    scanner=Depends(get_scanner_user),
    db: AsyncSession = Depends(get_db),
):
    """Confirma la recepción de un albarán desde el escáner móvil."""
    try:
        return await svc.confirm_delivery(
            db, UUID(scanner["tenant_id"]), payload.albaran_number
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
