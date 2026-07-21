"""Registro de eventos del SIF (RD 1007/2023 Art. 14, Orden HAC/1177/2024).

Cadena append-only por tenant con huella SHA-256 — misma integridad que la de
facturas. Registra eventos del sistema: arranque/parada (funcionamiento como NO
VERI*FACTU), lanzamiento de la detección de anomalías, resumen periódico (cada 6h),
exportación y cambio de modo. La huella se calcula sobre una cadena canónica que
incluye la huella del evento anterior del mismo tenant → inalterabilidad y
trazabilidad.
"""

from __future__ import annotations

from collections import namedtuple
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.billing import SifEvent
from app.services.billing.verifactu_chain import compute_huella, find_tail_huella

# Tipos de evento exigidos por el reglamento (subconjunto operativo).
EVENT_ARRANQUE = "ARRANQUE"
EVENT_PARADA = "PARADA"
EVENT_DETECCION_ANOMALIAS = "DETECCION_ANOMALIAS"
EVENT_RESUMEN = "RESUMEN"
EVENT_EXPORTACION = "EXPORTACION"
EVENT_CAMBIO_MODO = "CAMBIO_MODO"

VALID_EVENTS = {
    EVENT_ARRANQUE,
    EVENT_PARADA,
    EVENT_DETECCION_ANOMALIAS,
    EVENT_RESUMEN,
    EVENT_EXPORTACION,
    EVENT_CAMBIO_MODO,
}

_EvLink = namedtuple("_EvLink", ["huella", "huella_anterior"])


def build_payload_evento(*, tipo_evento: str, fecha_hora_gen: str, detalle: str, huella_anterior: str | None) -> str:
    """Cadena canónica del evento sobre la que se aplica SHA-256 (hex mayúsculas)."""
    return (
        f"TipoEvento={tipo_evento}"
        f"&FechaHoraHusoGenRegistro={fecha_hora_gen}"
        f"&Detalle={detalle or ''}"
        f"&HuellaAnterior={huella_anterior or ''}"
    )


async def _get_last_event_huella(db: AsyncSession, tenant_id: UUID) -> str | None:
    """Huella de la cola de la cadena de eventos del tenant (por enlace, no por
    marca de tiempo → inmune a timestamps idénticos), o None si no hay eventos."""
    result = await db.execute(select(SifEvent.huella, SifEvent.huella_anterior).where(SifEvent.tenant_id == tenant_id))
    links = [_EvLink(huella=h, huella_anterior=hp) for h, hp in result.all()]
    return find_tail_huella(links)


async def record_event(db: AsyncSession, *, tenant_id: UUID, tipo_evento: str, detalle: str = "") -> SifEvent:
    """Registra un evento del SIF encadenado. El caller debe estar en una
    transacción abierta (no hace commit). Concurrencia protegida con advisory lock
    por tenant en Postgres (SQLite es single-writer)."""
    if tipo_evento not in VALID_EVENTS:
        raise ValueError(f"Tipo de evento inválido: {tipo_evento}")

    dialect_name = db.bind.dialect.name if db.bind is not None else ""
    if dialect_name == "postgresql":
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": f"sifevent:{tenant_id}"},
        )

    huella_anterior = await _get_last_event_huella(db, tenant_id)
    now = datetime.now(UTC)
    fecha_hora_gen = now.astimezone().replace(microsecond=0).isoformat()
    payload = build_payload_evento(
        tipo_evento=tipo_evento,
        fecha_hora_gen=fecha_hora_gen,
        detalle=detalle,
        huella_anterior=huella_anterior,
    )
    huella = compute_huella(payload)

    event = SifEvent(
        tenant_id=tenant_id,
        tipo_evento=tipo_evento,
        detalle=detalle or None,
        huella=huella,
        huella_anterior=huella_anterior,
        payload_canonico=payload,
        fecha_hora=now,
    )
    db.add(event)
    await db.flush()
    return event


async def verify_events_integrity(db: AsyncSession, tenant_id: UUID) -> tuple[bool, int]:
    """Recomputa la huella de cada evento y verifica que la cadena no fue alterada.
    Devuelve `(ok, num_eventos)`."""
    result = await db.execute(select(SifEvent).where(SifEvent.tenant_id == tenant_id).order_by(SifEvent.created_at))
    events = list(result.scalars().all())
    for ev in events:
        if compute_huella(ev.payload_canonico) != ev.huella:
            return False, len(events)
    return True, len(events)
