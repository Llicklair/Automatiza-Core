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
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, text
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
EVENT_RESTAURACION = "RESTAURACION"

VALID_EVENTS = {
    EVENT_ARRANQUE,
    EVENT_PARADA,
    EVENT_DETECCION_ANOMALIAS,
    EVENT_RESUMEN,
    EVENT_EXPORTACION,
    EVENT_CAMBIO_MODO,
    EVENT_RESTAURACION,
}

_EvLink = namedtuple("_EvLink", ["huella", "huella_anterior"])


def build_payload_evento(
    *,
    nif_productor: str,
    id_sistema: str,
    version: str,
    num_instalacion: str,
    nif_obligado: str,
    tipo_evento: str,
    huella_anterior: str | None,
    fecha_hora_gen: str,
    detalle: str,
) -> str:
    """Cadena canónica del evento sobre la que se aplica SHA-256 (hex mayúsculas).

    Campos y orden del art. 13.1.c Orden HAC/1177/2024: productor, id del SIF,
    versión, número de instalación, NIF del obligado, tipo de evento, huella del
    evento anterior y fecha-hora-huso. `Detalle` va al final para que la huella
    también proteja el contenido del evento."""
    return (
        f"NIFProductor={nif_productor}"
        f"&IDSistemaInformatico={id_sistema}"
        f"&Version={version}"
        f"&NumeroInstalacion={num_instalacion}"
        f"&NIFObligado={nif_obligado}"
        f"&TipoEvento={tipo_evento}"
        f"&HuellaAnterior={huella_anterior or ''}"
        f"&FechaHoraHusoGenRegistro={fecha_hora_gen}"
        f"&Detalle={detalle or ''}"
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

    # Identificación exigida en el payload del evento (art. 13.1.c): productor +
    # sistema desde settings; NIF del obligado desde el tenant (puede faltar en
    # modo no_remission — el evento se registra igual, es de sistema).
    from app.db.models.auth import Tenant
    from app.services.billing.registro_facturacion import default_sistema_informatico
    from app.services.billing.verifactu_chain import TZ_EXPEDICION

    sif = default_sistema_informatico()
    tenant = await db.get(Tenant, tenant_id)
    nif_obligado = (tenant.nif if tenant is not None else "") or ""

    now = datetime.now(TZ_EXPEDICION)
    fecha_hora_gen = now.replace(microsecond=0).isoformat()
    payload = build_payload_evento(
        nif_productor=sif.nif,
        id_sistema=sif.id_sistema,
        version=sif.version,
        num_instalacion=sif.numero_instalacion,
        nif_obligado=nif_obligado,
        tipo_evento=tipo_evento,
        huella_anterior=huella_anterior,
        fecha_hora_gen=fecha_hora_gen,
        detalle=detalle,
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
    """Verifica que la cadena de eventos no fue alterada. Tres comprobaciones:
    (1) huella == SHA-256(payload) de cada evento; (2) la columna
    `huella_anterior` coincide con la hasheada en el payload (una fila reescrita
    de forma internamente consistente no cuela); (3) los enlaces forman UNA sola
    cadena génesis→cola, sin ciclos ni bifurcaciones. Devuelve `(ok, n)`."""
    from app.services.billing.verifactu_chain import order_verifactu_chain

    result = await db.execute(select(SifEvent).where(SifEvent.tenant_id == tenant_id))
    events = list(result.scalars().all())
    for ev in events:
        if compute_huella(ev.payload_canonico) != ev.huella:
            return False, len(events)
        # Enlace columna↔payload (compat con el formato antiguo, que terminaba
        # en HuellaAnterior, y el nuevo, que sigue con FechaHora...).
        marca = f"&HuellaAnterior={ev.huella_anterior or ''}"
        if f"{marca}&" not in ev.payload_canonico and not ev.payload_canonico.endswith(marca):
            return False, len(events)
    _, bien_formada = order_verifactu_chain(events)
    if not bien_formada:
        return False, len(events)
    return True, len(events)


async def detect_anomalies(db: AsyncSession, *, tenant_id: UUID) -> SifEvent | None:
    """Detección de anomalías (RD 1007/2023 Art. 14): verifica la integridad de la
    cadena de facturas y la de eventos. Si alguna está alterada, registra un evento
    DETECCION_ANOMALIAS y lo devuelve; si todo está íntegro, devuelve None."""
    from app.services.billing.verifactu_chain import verify_chain_integrity

    ok_fact, _ = await verify_chain_integrity(db, tenant_id)
    ok_ev, _ = await verify_events_integrity(db, tenant_id)
    if ok_fact and ok_ev:
        return None

    partes = []
    if not ok_fact:
        partes.append("cadena de facturas")
    if not ok_ev:
        partes.append("cadena de eventos")
    return await record_event(
        db,
        tenant_id=tenant_id,
        tipo_evento=EVENT_DETECCION_ANOMALIAS,
        detalle="anomalía de integridad en " + ", ".join(partes),
    )


async def record_periodic_summary(db: AsyncSession, *, tenant_id: UUID) -> SifEvent:
    """Evento RESUMEN periódico (RD: al menos uno por cada 6 h de operación), con el
    recuento de registros de facturación y de eventos del tenant hasta la fecha."""
    from app.db.models.billing import VerifactuRecord

    n_reg = (
        await db.execute(select(func.count(VerifactuRecord.id)).where(VerifactuRecord.tenant_id == tenant_id))
    ).scalar() or 0
    n_ev = (await db.execute(select(func.count(SifEvent.id)).where(SifEvent.tenant_id == tenant_id))).scalar() or 0
    return await record_event(
        db,
        tenant_id=tenant_id,
        tipo_evento=EVENT_RESUMEN,
        detalle=f"facturas={n_reg} eventos={n_ev}",
    )
