"""Exportación / conservación de registros (RD 1007/2023 art. 8.2.c, Orden art. 8.2).

El SIF debe poder exportar todos los registros de facturación y de eventos de un
periodo, como copia fidedigna y legible. Cada exportación genera su evento
correspondiente (Orden art. 9.1.h para los registros de facturación, art. 9.1.i para
los de evento).

`export_periodo()` devuelve el volcado íntegro (payload canónico + huella) de
facturas y eventos. `export_periodo_xml()` produce, para las facturas, el formato del
anexo (apartado 3): el `RegistroAlta` "pelado". Pendiente menor: el `RegistroEvento`
del anexo (apartado 5) — hoy los eventos se exportan como payload + huella (íntegro),
falta envolverlos en su XML exacto (requiere la estructura de campos del ap. 5).
"""

from __future__ import annotations

from datetime import UTC, datetime
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


async def export_periodo_xml(db: AsyncSession, *, tenant_id: UUID, desde: datetime, hasta: datetime) -> str:
    """Exporta los registros de facturación del periodo en el formato del anexo
    (apartado 3): cada uno como su elemento `RegistroAlta` "pelado" (sin la Cabecera,
    que solo aplica a la remisión), reutilizando el builder oficial del registro.
    Registra el evento de exportación de facturas (Orden art. 9.1.h)."""
    from xml.etree.ElementTree import Element, fromstring, tostring

    from sqlalchemy.orm import selectinload

    from app.db.models.auth import Tenant
    from app.db.models.billing import Invoice
    from app.services.billing.registro_facturacion import NS_SF, build_registro_alta_xml

    tenant = await db.get(Tenant, tenant_id)
    emisor_nombre = tenant.name if tenant else ""

    # Todos los registros hasta `hasta` para poder mapear la huella anterior (prev).
    all_recs = (
        (
            await db.execute(
                select(VerifactuRecord)
                .where(VerifactuRecord.tenant_id == tenant_id, VerifactuRecord.fecha_emision <= hasta)
                .order_by(VerifactuRecord.created_at)
            )
        )
        .scalars()
        .all()
    )
    by_huella = {r.huella: r for r in all_recs}

    # SQLite guarda los DateTime como naive; normalizamos la zona para comparar con
    # `desde` (que puede venir tz-aware) sin romper.
    def _aware(dt: datetime) -> datetime:
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)

    periodo_recs = [r for r in all_recs if _aware(r.fecha_emision) >= _aware(desde)]

    root = Element("ExportacionRegistrosFacturacion")
    for rec in periodo_recs:
        inv = (
            await db.execute(
                select(Invoice)
                .options(selectinload(Invoice.lines), selectinload(Invoice.client))
                .where(Invoice.id == rec.invoice_id)
            )
        ).scalar_one_or_none()
        if inv is None:
            continue
        prev = by_huella.get(rec.huella_anterior) if rec.huella_anterior else None
        rectified = await db.get(Invoice, inv.rectifies_invoice_id) if inv.rectifies_invoice_id else None
        substituted = await db.get(Invoice, inv.substitutes_invoice_id) if inv.substitutes_invoice_id else None
        full = build_registro_alta_xml(
            record=rec,
            invoice=inv,
            emisor_nombre=emisor_nombre,
            lines=inv.lines,
            prev_record=prev,
            rectified_invoice=rectified,
            substituted_invoice=substituted,
            destinatario_nombre=getattr(inv.client, "name", None),
            destinatario_nif=getattr(inv.client, "nif", None),
        )
        alta = fromstring(full).find(f".//{{{NS_SF}}}RegistroAlta")
        if alta is not None:
            root.append(alta)

    xml = tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")
    await record_event(
        db,
        tenant_id=tenant_id,
        tipo_evento=EVENT_EXPORTACION,
        detalle=f"XML facturas {desde.date()}..{hasta.date()} n={len(periodo_recs)}",
    )
    return xml
