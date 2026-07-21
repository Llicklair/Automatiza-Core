"""Cadena hash Verifactu (FAC.HASH) — RD 1007/2023 Art. 8.

Cada factura genera un registro append-only en `verifactu_chain` con un
`huella` SHA-256 que encadena al `huella_anterior` del último registro del
mismo tenant. La cadena es independiente por tenant.

Concurrencia: `pg_advisory_xact_lock` por `tenant_id` evita que dos
transacciones emitan registros con la misma `huella_anterior`. SQLite no
necesita lock (single-writer por diseño).
"""

from __future__ import annotations

import hashlib
from collections import namedtuple
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.billing import VerifactuRecord

# Huso del territorio de expedición (art. 11 Orden HAC/1177/2024): fijo a
# Europe/Madrid, no la tz del SO (un despliegue con TZ=UTC emitía +00:00).
TZ_EXPEDICION = ZoneInfo("Europe/Madrid")

if TYPE_CHECKING:  # pragma: no cover
    from app.db.models.billing import Invoice


def _fmt_importe(x) -> str:
    """Importe con punto decimal y 2 decimales (p.ej. ``123.45``)."""
    return f"{Decimal(x if x is not None else 0):.2f}"


def _fmt_fecha_expedicion(dt) -> str:
    """Fecha de expedición en formato ``dd-mm-yyyy`` que exige la AEAT."""
    return dt.strftime("%d-%m-%Y") if dt is not None else ""


def _fmt_fecha_hora_gen(dt) -> str:
    """``FechaHoraHusoGenRegistro``: ISO 8601 con huso y sin microsegundos
    (p.ej. ``2024-01-01T19:20:30+01:00``)."""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.replace(microsecond=0).isoformat()


def build_payload_alta(
    *,
    id_emisor: str,
    num_serie_factura: str,
    fecha_expedicion: str,
    tipo_factura: str,
    cuota_total,
    importe_total,
    huella_anterior: str | None,
    fecha_hora_gen: str,
) -> str:
    """Cadena canónica de un Registro de Alta (Veri*Factu, AEAT).

    Formato oficial: pares ``nombre=valor`` unidos por ``&``, en el orden fijado
    por la especificación de la AEAT, importes con punto y 2 decimales y huella
    anterior vacía si es el primer registro del tenant. Sobre esta cadena
    (UTF-8) se aplica SHA-256 y el resultado se expresa en hex MAYÚSCULAS.

    Validado contra el vector de prueba publicado por la AEAT (ver
    ``tests/test_verifactu_chain.py::TestVectorOficialAEAT``).
    """
    parts = [
        f"IDEmisorFactura={(id_emisor or '').strip()}",
        f"NumSerieFactura={(num_serie_factura or '').strip()}",
        f"FechaExpedicionFactura={fecha_expedicion}",
        f"TipoFactura={(tipo_factura or '').strip()}",
        f"CuotaTotal={_fmt_importe(cuota_total)}",
        f"ImporteTotal={_fmt_importe(importe_total)}",
        f"Huella={huella_anterior or ''}",
        f"FechaHoraHusoGenRegistro={fecha_hora_gen}",
    ]
    return "&".join(parts)


def build_payload_anulacion(
    *,
    id_emisor: str,
    num_serie_factura: str,
    fecha_expedicion: str,
    huella_anterior: str | None,
    fecha_hora_gen: str,
) -> str:
    """Cadena canónica de un Registro de Anulación (Veri*Factu, AEAT).

    Mismo tratamiento que el alta, pero con el subconjunto de campos que la
    especificación define para la anulación de un registro previamente emitido.
    """
    parts = [
        f"IDEmisorFacturaAnulada={(id_emisor or '').strip()}",
        f"NumSerieFacturaAnulada={(num_serie_factura or '').strip()}",
        f"FechaExpedicionFacturaAnulada={fecha_expedicion}",
        f"Huella={huella_anterior or ''}",
        f"FechaHoraHusoGenRegistro={fecha_hora_gen}",
    ]
    return "&".join(parts)


def compute_huella(payload_canonico: str) -> str:
    """SHA-256 del payload canónico en hex MAYÚSCULAS (64 chars).

    La especificación de la AEAT exige el resultado en mayúsculas.
    """
    return hashlib.sha256(payload_canonico.encode("utf-8")).hexdigest().upper()


# Vista ligera (huella, huella_anterior) para razonar sobre el orden de la
# cadena sin cargar filas completas.
_Link = namedtuple("_Link", ["huella", "huella_anterior"])


def order_verifactu_chain(records: list) -> tuple[list, bool]:
    """Ordena los registros siguiendo el ENLACE hash (`huella_anterior` →
    `huella`), no el `created_at`.

    Una cadena hash define su propio orden. Ordenar por `created_at` era frágil:
    dos registros con la misma marca de tiempo (algo posible bajo carga, o si la
    BD trunca la precisión) producían un orden no determinista que rompía el
    encadenado al emitir y daba falsos negativos al verificar.

    `records`: objetos con atributos `huella` y `huella_anterior`.
    Devuelve `(ordenados, bien_formada)`:
      - `ordenados`: del génesis (`huella_anterior` None/"") hasta la cola.
      - `bien_formada`: True si forman UNA sola cadena —sin ciclos ni
        bifurcaciones— que cubre TODOS los registros.
    Si está mal formada, `ordenados` contiene lo reconstruible y la bandera es
    False (lo aprovecha la verificación de integridad para detectar roturas).
    """
    records = list(records)
    if not records:
        return [], True

    successors: dict = {}
    for r in records:
        successors.setdefault(r.huella_anterior or None, []).append(r)

    genesis = successors.get(None, [])
    if len(genesis) != 1:
        # Cero génesis (ciclo total) o varios (cadena bifurcada/duplicada).
        return [], False

    ordered: list = []
    seen: set = set()
    cur = genesis[0]
    while cur is not None:
        if cur.huella in seen:
            return ordered, False  # ciclo
        ordered.append(cur)
        seen.add(cur.huella)
        nxt = successors.get(cur.huella, [])
        if len(nxt) == 0:
            cur = None
        elif len(nxt) == 1:
            cur = nxt[0]
        else:
            return ordered, False  # bifurcación

    return ordered, len(ordered) == len(records)


def find_tail_huella(records: list) -> str | None:
    """Devuelve la `huella` de la cola de la cadena (la huella que no es
    `huella_anterior` de ningún registro), o None si no hay registros.

    Es el punto al que debe encadenar el siguiente registro. Independiente de
    `created_at`, por lo que es inmune a marcas de tiempo idénticas.
    """
    records = list(records)
    if not records:
        return None
    referenced = {r.huella_anterior for r in records}
    tails = [r for r in records if r.huella not in referenced]
    if len(tails) == 1:
        return tails[0].huella
    # 0 colas (ciclo) o >1 (cadena rota): reconstruir por enlace y tomar la
    # última posición reconstruible como mejor aproximación determinista.
    ordered, _ok = order_verifactu_chain(records)
    return ordered[-1].huella if ordered else None


async def _get_last_huella(db: AsyncSession, tenant_id: UUID) -> str | None:
    """Devuelve la `huella` de la cola de la cadena del tenant, o None si no hay.

    Se determina por el enlace de la cadena (no por `created_at`), de modo que
    dos registros con idéntica marca de tiempo no puedan provocar un encadenado
    incorrecto. Carga solo (huella, huella_anterior): O(n) por alta, suficiente
    para volúmenes de pyme.
    """
    result = await db.execute(
        select(VerifactuRecord.huella, VerifactuRecord.huella_anterior).where(VerifactuRecord.tenant_id == tenant_id)
    )
    links = [_Link(huella=h, huella_anterior=hp) for h, hp in result.all()]
    return find_tail_huella(links)


async def append_verifactu_record(
    db: AsyncSession,
    *,
    invoice: Invoice,
    nif_emisor: str,
) -> VerifactuRecord:
    """Genera y persiste el siguiente registro Verifactu encadenado.

    El caller DEBE estar dentro de una transacción abierta. La función:
      1. Toma `pg_advisory_xact_lock` por `tenant_id` (Postgres).
      2. Lee la `huella` del último registro del tenant.
      3. Construye el payload canónico con la `huella_anterior`.
      4. Calcula la nueva `huella` y persiste el registro.

    Si el `invoice` ya tiene un registro Verifactu, se devuelve el existente
    en lugar de duplicar (idempotencia ante reintentos).
    """
    # Idempotencia: si ya hay registro para esta factura, devolverlo.
    existing = await db.execute(select(VerifactuRecord).where(VerifactuRecord.invoice_id == invoice.id))
    existing_row = existing.scalar_one_or_none()
    if existing_row is not None:
        return existing_row

    dialect_name = db.bind.dialect.name if db.bind is not None else ""
    if dialect_name == "postgresql":
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": f"verifactu:{invoice.tenant_id}"},
        )

    huella_anterior = await _get_last_huella(db, invoice.tenant_id)

    # `NumSerieFactura` (oficial) es serie+número, que es justo nuestro
    # invoice_number. La serie explícita se infiere para el campo de display.
    invoice_number = invoice.invoice_number or ""
    serie = "".join(ch for ch in invoice_number if not ch.isdigit() and ch != "-")[:16] or "A"

    # TipoFactura (lista L2): R1 rectificativa de completa / R5 de simplificada
    # (RD 1619/2012 Art. 15); F3 sustitutiva; F2 simplificada / ticket TPV (sin
    # destinatario identificado); F1 completa.
    if (invoice.invoice_type or "").lower() == "rectificativa":
        tipo_factura = "R1"
        rectifies_id = getattr(invoice, "rectifies_invoice_id", None)
        if rectifies_id is not None:
            from app.db.models.billing import Invoice as _Invoice

            rect_simpl = (
                await db.execute(select(_Invoice.is_simplified).where(_Invoice.id == rectifies_id))
            ).scalar_one_or_none()
            if rect_simpl:
                tipo_factura = "R5"
    elif getattr(invoice, "substitutes_invoice_id", None):
        tipo_factura = "F3"
    elif invoice.is_simplified:
        tipo_factura = "F2"
    else:
        tipo_factura = "F1"
    cuota = invoice.tax_amount if invoice.tax_amount is not None else Decimal("0.00")
    importe = invoice.amount_total if invoice.amount_total is not None else Decimal("0.00")

    payload = build_payload_alta(
        id_emisor=nif_emisor,
        num_serie_factura=invoice_number,
        fecha_expedicion=_fmt_fecha_expedicion(invoice.date),
        tipo_factura=tipo_factura,
        cuota_total=cuota,
        importe_total=importe,
        huella_anterior=huella_anterior,
        fecha_hora_gen=_fmt_fecha_hora_gen(datetime.now(TZ_EXPEDICION)),
    )
    huella = compute_huella(payload)

    record = VerifactuRecord(
        tenant_id=invoice.tenant_id,
        invoice_id=invoice.id,
        huella=huella,
        huella_anterior=huella_anterior,
        payload_canonico=payload,
        nif_emisor=nif_emisor,
        serie_factura=serie,
        numero_factura=invoice_number,
        fecha_emision=invoice.date,
        importe_total=importe,
    )
    db.add(record)
    await db.flush()
    return record


async def maybe_append_verifactu_record(
    db: AsyncSession,
    *,
    invoice: Invoice,
) -> VerifactuRecord | None:
    """Si el tenant está en modo Verifactu "voluntary", añade la entrada
    encadenada para esta factura. Si está en "no_remission" no hace nada.

    Carga el NIF emisor desde el Tenant para construir la huella canónica.
    El caller debe estar dentro de una transacción abierta (no hace commit).
    Idempotente: si ya hay registro para la factura, devuelve el existente.

    Devuelve el `VerifactuRecord` creado/existente, o `None` si el tenant
    está en modo `no_remission`.
    """
    from app.db.models.auth import Tenant
    from app.services.billing.verifactu_mode import should_remit

    if not await should_remit(db, tenant_id=invoice.tenant_id):
        return None

    tenant = await db.get(Tenant, invoice.tenant_id)
    if tenant is None or not tenant.nif:
        # Verifactu activo ("voluntary") obliga a registrar. Sin NIF del emisor no
        # se puede firmar el payload canónico → antes se omitía con un warning y la
        # factura se emitía SIN registro (agujero de doble uso, art. 201 bis LGT).
        # Ahora se bloquea la emisión: fail-closed.
        raise ValueError(
            "Verifactu está activo pero el tenant no tiene NIF de emisor configurado; "
            "no se puede emitir la factura sin él. Configura el NIF fiscal del negocio."
        )

    return await append_verifactu_record(db, invoice=invoice, nif_emisor=tenant.nif)


async def ensure_verifactu_on_expedition(
    db: AsyncSession,
    invoice: Invoice,
) -> VerifactuRecord | None:
    """Aplica las guardas de EXPEDICIÓN y encadena si procede.

    Punto único de decisión para todos los caminos que expiden facturas
    (create_invoice no-borrador, update_status, conciliación bancaria,
    importación masiva): solo encadena facturas EMITIDAS (issued/rectificativa),
    nunca recibidas ni demo, y nunca borradores (la expedición es el hecho
    fiscal; un borrador aún no está expedido). Idempotente; fail-closed sin
    NIF en modo voluntary (ValueError). En "no_remission" es un no-op.
    """
    from app.services.billing.constants import EMITTED_INVOICE_TYPES

    if (invoice.invoice_type or "issued") not in EMITTED_INVOICE_TYPES:
        return None
    if invoice.is_demo:
        return None
    if (invoice.status or "draft") in ("draft", "cancelled"):
        return None
    return await maybe_append_verifactu_record(db, invoice=invoice)


async def verify_chain_integrity(db: AsyncSession, tenant_id: UUID) -> tuple[bool, int]:
    """Recorre la cadena completa del tenant y verifica integridad.

    Devuelve `(ok, num_records_verified)`. `ok=False` significa que algún
    registro tiene una `huella` que no coincide con el SHA-256 recomputado
    desde el `payload_canonico`, o que la `huella_anterior` no enlaza con el
    registro previo en orden cronológico.
    """
    result = await db.execute(select(VerifactuRecord).where(VerifactuRecord.tenant_id == tenant_id))
    rows = list(result.scalars().all())

    # El orden lo da el enlace de la cadena, no `created_at`. Si la cadena no
    # está bien formada (génesis ausente/múltiple, ciclo, bifurcación o algún
    # registro huérfano que no encadena), es una rotura de integridad.
    ordered, well_formed = order_verifactu_chain(rows)
    if not well_formed:
        return False, len(rows)

    expected_prev: str | None = None
    for record in ordered:
        if (record.huella_anterior or None) != expected_prev:
            return False, len(rows)
        if compute_huella(record.payload_canonico) != record.huella:
            return False, len(rows)
        expected_prev = record.huella

    return True, len(rows)
