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
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.billing import DeliveryNote
from app.db.models.inventory import Product, StockMovement
from app.middleware.rate_limit import limiter
from app.middleware.scanner_auth import (
    create_scanner_token,
    get_scanner_user,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────


class GenerateQRRequest(BaseModel):
    device_name: str = "Scanner móvil"


class ScanProductRequest(BaseModel):
    sku: str


class StockMovementRequest(BaseModel):
    sku: str
    quantity: float
    notes: str = ""


class ConfirmDeliveryRequest(BaseModel):
    albaran_number: str


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
    # El frontend generará el QR con este token
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
    tenant_id = UUID(scanner["tenant_id"])
    result = await db.execute(
        select(Product).where(
            Product.tenant_id == tenant_id,
            Product.sku == payload.sku,
        )
    )
    product = result.scalars().first()
    if not product:
        raise HTTPException(
            status_code=404, detail=f"Producto con SKU '{payload.sku}' no encontrado"
        )

    return {
        "id": str(product.id),
        "sku": product.sku,
        "name": product.name,
        "description": product.description,
        "price": float(product.price) if product.price else None,
        "stock_quantity": float(product.stock_quantity) if product.stock_quantity else 0,
        "stock_min_alert": float(product.stock_min_alert) if product.stock_min_alert else None,
        "low_stock": (
            product.stock_min_alert is not None
            and product.stock_quantity is not None
            and product.stock_quantity <= product.stock_min_alert
        ),
    }


@router.post("/stock-entry")
@limiter.limit("30/minute")
async def stock_entry(
    request: Request,
    payload: StockMovementRequest,
    scanner=Depends(get_scanner_user),
    db: AsyncSession = Depends(get_db),
):
    """Registra entrada de stock desde el escáner móvil."""
    return await _record_movement(db, scanner, payload, "entrada")


@router.post("/stock-exit")
@limiter.limit("30/minute")
async def stock_exit(
    request: Request,
    payload: StockMovementRequest,
    scanner=Depends(get_scanner_user),
    db: AsyncSession = Depends(get_db),
):
    """Registra salida de stock desde el escáner móvil."""
    return await _record_movement(db, scanner, payload, "salida")


@router.post("/confirm-delivery")
@limiter.limit("10/minute")
async def confirm_delivery(
    request: Request,
    payload: ConfirmDeliveryRequest,
    scanner=Depends(get_scanner_user),
    db: AsyncSession = Depends(get_db),
):
    """Confirma la recepción de un albarán desde el escáner móvil."""
    tenant_id = UUID(scanner["tenant_id"])
    result = await db.execute(
        select(DeliveryNote).where(
            DeliveryNote.tenant_id == tenant_id,
            DeliveryNote.albaran_number == payload.albaran_number,
        )
    )
    albaran = result.scalars().first()
    if not albaran:
        raise HTTPException(
            status_code=404, detail=f"Albarán '{payload.albaran_number}' no encontrado"
        )

    if albaran.status == "delivered":
        return {"status": "already_delivered", "albaran_number": albaran.albaran_number}

    albaran.status = "delivered"
    await db.commit()

    return {
        "status": "confirmed",
        "albaran_number": albaran.albaran_number,
        "previous_status": "confirmed" if albaran.status != "draft" else "draft",
        "client_name": albaran.client_name if hasattr(albaran, "client_name") else None,
    }


# ── Helper ───────────────────────────────────────────────────────────────────


async def _record_movement(
    db: AsyncSession,
    scanner: dict,
    payload: StockMovementRequest,
    movement_type: str,
) -> dict:
    """Registra un movimiento de stock y actualiza la cantidad."""
    tenant_id = UUID(scanner["tenant_id"])
    result = await db.execute(
        select(Product).where(
            Product.tenant_id == tenant_id,
            Product.sku == payload.sku,
        )
    )
    product = result.scalars().first()
    if not product:
        raise HTTPException(
            status_code=404, detail=f"Producto con SKU '{payload.sku}' no encontrado"
        )

    current_stock = float(product.stock_quantity or 0)
    qty = abs(payload.quantity)

    if movement_type == "entrada":
        new_stock = current_stock + qty
    else:
        if qty > current_stock:
            raise HTTPException(
                status_code=400, detail=f"Stock insuficiente ({current_stock} < {qty})"
            )
        new_stock = current_stock - qty

    product.stock_quantity = new_stock

    movement = StockMovement(
        product_id=product.id,
        movement_type=movement_type,
        quantity=qty if movement_type == "entrada" else -qty,
        stock_after=new_stock,
        reference=f"scanner:{scanner.get('device', 'mobile')}",
        notes=payload.notes or f"Movimiento vía escáner ({movement_type})",
    )
    db.add(movement)
    await db.commit()

    return {
        "product_id": str(product.id),
        "sku": product.sku,
        "name": product.name,
        "movement_type": movement_type,
        "quantity": qty,
        "stock_before": current_stock,
        "stock_after": new_stock,
        "low_stock": (
            product.stock_min_alert is not None and new_stock <= float(product.stock_min_alert)
        ),
    }
