"""Exportación / conservación de registros (RD 1007/2023 art. 8.2.c, Orden art. 8.2).

El SIF debe poder exportar todos los registros de facturación y de eventos de un
periodo, como copia fidedigna y legible. Cada exportación genera su evento
correspondiente (Orden art. 9.1.h para los registros de facturación, art. 9.1.i para
los de evento).

Esta exportación preserva, por cada registro, su `payload_canonico` (el contenido
exacto que se hashea) y su `huella` (integridad), más la metadata clave. NOTA:
envolver cada registro en el XML exacto del anexo (RegistroAlta/RegistroEvento
"pelado", apartados 3 y 5) es un refinamiento pendiente; el contenido íntegro
(payload + huella) sí se exporta fielmente.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.billing import SifEvent, VerifactuRecord
from app.services.billing.sif_events import EVENT_EXPORTACION, record_event


async def export_periodo(db: AsyncSession, *, tenant_id: UUID, desde: datetime, hasta: datetime) -> dict:
    """Exporta los registros de facturación y de eventos del tenant en [desde, hasta]
    y registra los eventos de exportación. El caller debe estar en transacción (no
    hace commit). Devuelve la exportación como dict serializable."""
    recs = (
        (
            await db.execute(
                select(VerifactuRecord)
                .where(
                    VerifactuRecord.tenant_id == tenant_id,
                    VerifactuRecord.fecha_emision >= desde,
                    VerifactuRecord.fecha_emision <= hasta,
                )
                .order_by(VerifactuRecord.created_at)
            )
        )
        .scalars()
        .all()
    )
    evs = (
        (
            await db.execute(
                select(SifEvent)
                .where(
                    SifEvent.tenant_id == tenant_id,
                    SifEvent.fecha_hora >= desde,
                    SifEvent.fecha_hora <= hasta,
                )
                .order_by(SifEvent.created_at)
            )
        )
        .scalars()
        .all()
    )

    export = {
        "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        "registros_facturacion": [
            {
                "huella": r.huella,
                "huella_anterior": r.huella_anterior,
                "payload_canonico": r.payload_canonico,
                "numero_factura": r.numero_factura,
                "fecha_emision": r.fecha_emision.isoformat(),
            }
            for r in recs
        ],
        "registros_evento": [
            {
                "huella": e.huella,
                "huella_anterior": e.huella_anterior,
                "payload_canonico": e.payload_canonico,
                "tipo_evento": e.tipo_evento,
                "fecha_hora": e.fecha_hora.isoformat(),
            }
            for e in evs
        ],
        "counts": {"facturas": len(recs), "eventos": len(evs)},
    }

    # Eventos de exportación (Orden art. 9.1.h y 9.1.i). Se recogen ANTES de
    # registrarse, por lo que no se autoincluyen en la exportación.
    periodo = f"{desde.date()}..{hasta.date()}"
    await record_event(
        db, tenant_id=tenant_id, tipo_evento=EVENT_EXPORTACION, detalle=f"facturas periodo {periodo} n={len(recs)}"
    )
    await record_event(
        db, tenant_id=tenant_id, tipo_evento=EVENT_EXPORTACION, detalle=f"eventos periodo {periodo} n={len(evs)}"
    )

    return export
