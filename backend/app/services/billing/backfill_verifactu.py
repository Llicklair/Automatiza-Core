"""Backfill histórico de la cadena Verifactu (A.5).

Reconstruye `verifactu_chain` retroactivamente para tenants que importaron
facturas desde Holded / A3 / CSV ANTES de la activación de FAC.HASH.

Reglas de diseño consensuadas en Ronda 18:

* **Cronológico estricto**: las facturas se procesan ordenadas por
  `date ASC, created_at ASC, invoice_number ASC` (desempate determinista)
  para que la cadena sea reproducible.
* **Marca explícita**: cada registro generado lleva `is_backfilled=True`
  con `backfilled_at=NOW()`, distinguible del registro firmado en tiempo
  real. La AEAT acepta backfill siempre que sea auditable.
* **Idempotente**: si una factura ya tiene registro en `verifactu_chain`,
  se respeta y se continúa la cadena. Permite reintentar tras un crash sin
  riesgo de duplicar o romper la integridad.
* **Append-only respetado**: los triggers PL/pgSQL de la migración 0011
  siguen activos — el backfill solo inserta, nunca actualiza.
* **Sin firma falsa**: la `fecha_emision` del registro es la real de la
  factura, pero el `backfilled_at` y `is_backfilled` documentan que el
  hash se calculó a posteriori. Esto es lo que distingue backfill legítimo
  de manipulación.

Concurrencia: una sola corrida por tenant. El advisory_xact_lock por
`tenant_id` previene que dos backfills concurrentes pisen la cadena.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import asc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.billing import Invoice, VerifactuRecord
from app.services.billing.verifactu_chain import build_payload_canonico, compute_huella

logger = logging.getLogger("billing.backfill_verifactu")


@dataclass
class BackfillResult:
    """Resumen del backfill ejecutado en un tenant."""

    tenant_id: UUID
    invoices_total: int
    already_chained: int
    backfilled: int
    started_at: datetime
    finished_at: datetime

    @property
    def is_empty(self) -> bool:
        return self.invoices_total == 0

    def to_dict(self) -> dict:
        return {
            "tenant_id": str(self.tenant_id),
            "invoices_total": self.invoices_total,
            "already_chained": self.already_chained,
            "backfilled": self.backfilled,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
        }


async def _is_backfill_needed(db: AsyncSession, tenant_id: UUID) -> bool:
    """`True` si el tenant tiene al menos una factura sin registro Verifactu."""
    result = await db.execute(
        select(Invoice.id)
        .outerjoin(
            VerifactuRecord,
            VerifactuRecord.invoice_id == Invoice.id,
        )
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_type == "issued",
            VerifactuRecord.id.is_(None),
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


def _infer_serie(invoice_number: str) -> str:
    """Extrae la serie del invoice_number con formato `{prefix}{year}-{NNNN}`.

    Espejo de la lógica de `append_verifactu_record` para mantener la
    cadena idéntica si una factura backfilleada se mezcla con una
    nueva en tiempo real.
    """
    return "".join(ch for ch in (invoice_number or "") if not ch.isdigit() and ch != "-")[:16] or "A"


async def backfill_tenant_verifactu_chain(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    nif_emisor: str,
) -> BackfillResult:
    """Reconstruye la cadena Verifactu para un tenant migrado.

    El caller DEBE estar dentro de una transacción abierta — la función
    no hace commit ni rollback. Si lanza, el caller debe rollback.

    Devuelve un `BackfillResult` con métricas. Es seguro re-ejecutar (las
    facturas ya encadenadas se saltan).
    """
    started_at = datetime.now(timezone.utc)

    # Lock por tenant para evitar dos backfills concurrentes.
    dialect_name = db.bind.dialect.name if db.bind is not None else ""
    if dialect_name == "postgresql":
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": f"verifactu_backfill:{tenant_id}"},
        )

    # Pull all `issued` invoices of the tenant in deterministic cronological order.
    invoices_query = await db.execute(
        select(Invoice)
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_type == "issued",
        )
        .order_by(
            asc(Invoice.date),
            asc(Invoice.created_at),
            asc(Invoice.invoice_number),
        )
    )
    invoices = list(invoices_query.scalars().all())
    invoices_total = len(invoices)

    # Pre-cargamos los registros ya existentes por invoice_id para detectar
    # idempotencia sin un query por factura.
    existing_query = await db.execute(
        select(VerifactuRecord)
        .where(VerifactuRecord.tenant_id == tenant_id)
    )
    existing_by_invoice = {
        record.invoice_id: record for record in existing_query.scalars().all()
    }
    already_chained = len(existing_by_invoice)

    # Si el tenant tiene registros previos pero ninguno fue backfill, encadenamos
    # detrás del último (los registros existentes deben ser por orden cronológico).
    last_huella: str | None = None
    if existing_by_invoice:
        # Ordenamos los existentes por created_at desc para obtener el último.
        from sqlalchemy import desc

        last_q = await db.execute(
            select(VerifactuRecord.huella)
            .where(VerifactuRecord.tenant_id == tenant_id)
            .order_by(desc(VerifactuRecord.created_at))
            .limit(1)
        )
        last_huella = last_q.scalar_one_or_none()

    backfilled_count = 0
    backfilled_at = datetime.now(timezone.utc)

    for invoice in invoices:
        if invoice.id in existing_by_invoice:
            # Ya tiene registro — actualizamos `last_huella` con el suyo para
            # encadenar correctamente las siguientes facturas backfilleadas.
            last_huella = existing_by_invoice[invoice.id].huella
            continue

        serie = _infer_serie(invoice.invoice_number or "")
        fecha_iso = invoice.date.isoformat() if invoice.date is not None else ""
        importe = invoice.amount_total if invoice.amount_total is not None else Decimal("0.00")

        payload = build_payload_canonico(
            nif_emisor=nif_emisor,
            serie_factura=serie,
            numero_factura=invoice.invoice_number or "",
            fecha_emision_iso=fecha_iso,
            importe_total=importe,
            huella_anterior=last_huella,
        )
        huella = compute_huella(payload)

        record = VerifactuRecord(
            tenant_id=tenant_id,
            invoice_id=invoice.id,
            huella=huella,
            huella_anterior=last_huella,
            payload_canonico=payload,
            nif_emisor=nif_emisor,
            serie_factura=serie,
            numero_factura=invoice.invoice_number or "",
            fecha_emision=invoice.date,
            importe_total=importe,
            is_backfilled=True,
            backfilled_at=backfilled_at,
        )
        db.add(record)
        last_huella = huella
        backfilled_count += 1

    await db.flush()
    finished_at = datetime.now(timezone.utc)

    logger.info(
        "verifactu_backfill tenant=%s invoices_total=%d already_chained=%d backfilled=%d",
        tenant_id,
        invoices_total,
        already_chained,
        backfilled_count,
    )

    return BackfillResult(
        tenant_id=tenant_id,
        invoices_total=invoices_total,
        already_chained=already_chained,
        backfilled=backfilled_count,
        started_at=started_at,
        finished_at=finished_at,
    )


async def list_tenants_pending_backfill(db: AsyncSession) -> list[UUID]:
    """Lista tenant_ids con al menos 1 factura `issued` sin registro Verifactu.

    Usado por el job APScheduler diario para detectar tenants migrados
    recientemente que aún no han sido backfilleados.
    """
    result = await db.execute(
        select(Invoice.tenant_id)
        .outerjoin(
            VerifactuRecord,
            VerifactuRecord.invoice_id == Invoice.id,
        )
        .where(
            Invoice.invoice_type == "issued",
            VerifactuRecord.id.is_(None),
        )
        .distinct()
    )
    return [row[0] for row in result.all()]
