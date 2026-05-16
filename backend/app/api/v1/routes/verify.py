"""Endpoint público de verificación Verifactu (FAC.QR).

`GET /api/v1/verify/{huella}` — sin autenticación. Permite a la AEAT, al
receptor de la factura o a cualquier inspector verificar que un registro
Verifactu existe en el sistema, y consultar los datos básicos asociados
(NIF emisor, número de factura, fecha, importe y huella).

El endpoint NO expone PII más allá de lo que ya consta en el documento
público de la factura — el cliente final ya posee esa información, y el
inspector la usa para cotejar contra la factura física.

Cumplimiento: RD 1007/2023 Art. 8 — el sistema de emisión debe permitir
verificar la integridad del registro de facturación a terceros legitimados.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models.billing import VerifactuRecord
from app.services.billing.verifactu_chain import compute_huella

router = APIRouter(prefix="/verify", tags=["verifactu-public"])


@router.get("/{huella}")
async def verify_invoice_by_huella(huella: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Verifica un registro Verifactu por su huella SHA-256.

    Devuelve los datos identificativos del registro si existe, junto con
    un flag `integrity_ok` que indica si la huella almacenada coincide con
    el SHA-256 recomputado del payload canónico.
    """
    huella = (huella or "").strip().lower()
    if len(huella) != 64 or not all(c in "0123456789abcdef" for c in huella):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Huella inválida — se espera SHA-256 hexadecimal (64 chars).",
        )

    result = await db.execute(
        select(VerifactuRecord).where(VerifactuRecord.huella == huella)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se ha encontrado ningún registro Verifactu con esa huella.",
        )

    integrity_ok = compute_huella(record.payload_canonico) == record.huella

    return {
        "huella": record.huella,
        "huella_anterior": record.huella_anterior,
        "nif_emisor": record.nif_emisor,
        "serie_factura": record.serie_factura,
        "numero_factura": record.numero_factura,
        "fecha_emision": record.fecha_emision.isoformat() if record.fecha_emision else None,
        "importe_total": str(record.importe_total),
        "integrity_ok": integrity_ok,
        "fecha_registro": record.created_at.isoformat() if record.created_at else None,
    }
