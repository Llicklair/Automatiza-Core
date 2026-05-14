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
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.billing import VerifactuRecord

if TYPE_CHECKING:  # pragma: no cover
    from app.db.models.billing import Invoice


def build_payload_canonico(
    nif_emisor: str,
    serie_factura: str,
    numero_factura: str,
    fecha_emision_iso: str,
    importe_total: Decimal,
    huella_anterior: str | None,
) -> str:
    """Construye el payload canónico que se hashea.

    Formato determinista: campos en orden fijo separados por `|`, con
    `importe_total` normalizado a 2 decimales y `huella_anterior` literal
    (cadena vacía si es el primer registro del tenant).

    El formato es opaco al esquema oficial AEAT — la versión definitiva del
    payload se ajustará cuando se valide contra el cert de pruebas (FAC.TST).
    Lo importante de este MVP es que la cadena exista, sea reconstruible, y
    detecte manipulaciones.
    """
    importe_norm = f"{Decimal(importe_total):.2f}"
    parts = [
        nif_emisor or "",
        serie_factura or "",
        numero_factura or "",
        fecha_emision_iso or "",
        importe_norm,
        huella_anterior or "",
    ]
    return "|".join(parts)


def compute_huella(payload_canonico: str) -> str:
    """SHA-256 hexadecimal (64 chars) del payload canónico."""
    return hashlib.sha256(payload_canonico.encode("utf-8")).hexdigest()


async def _get_last_huella(db: AsyncSession, tenant_id: UUID) -> str | None:
    """Devuelve la `huella` del último registro del tenant, o None si no hay."""
    result = await db.execute(
        select(VerifactuRecord.huella)
        .where(VerifactuRecord.tenant_id == tenant_id)
        .order_by(desc(VerifactuRecord.created_at))
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return row


async def append_verifactu_record(
    db: AsyncSession,
    *,
    invoice: "Invoice",
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
    existing = await db.execute(
        select(VerifactuRecord).where(VerifactuRecord.invoice_id == invoice.id)
    )
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

    # Extraer serie del invoice_number con formato "{prefix}{year}-{NNNN}" o legacy.
    # Para el MVP usamos invoice_number tal cual como `numero_factura`; la serie
    # explícita la inferimos de los primeros chars hasta el primer dígito.
    invoice_number = invoice.invoice_number or ""
    serie = "".join(ch for ch in invoice_number if not ch.isdigit() and ch != "-")[:16] or "A"

    fecha_iso = invoice.date.isoformat() if invoice.date is not None else ""
    importe = invoice.amount_total if invoice.amount_total is not None else Decimal("0.00")

    payload = build_payload_canonico(
        nif_emisor=nif_emisor,
        serie_factura=serie,
        numero_factura=invoice_number,
        fecha_emision_iso=fecha_iso,
        importe_total=importe,
        huella_anterior=huella_anterior,
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


async def verify_chain_integrity(db: AsyncSession, tenant_id: UUID) -> tuple[bool, int]:
    """Recorre la cadena completa del tenant y verifica integridad.

    Devuelve `(ok, num_records_verified)`. `ok=False` significa que algún
    registro tiene una `huella` que no coincide con el SHA-256 recomputado
    desde el `payload_canonico`, o que la `huella_anterior` no enlaza con el
    registro previo en orden cronológico.
    """
    result = await db.execute(
        select(VerifactuRecord)
        .where(VerifactuRecord.tenant_id == tenant_id)
        .order_by(VerifactuRecord.created_at)
    )
    rows = list(result.scalars().all())

    expected_prev: str | None = None
    for record in rows:
        if record.huella_anterior != expected_prev:
            return False, len(rows)
        if compute_huella(record.payload_canonico) != record.huella:
            return False, len(rows)
        expected_prev = record.huella

    return True, len(rows)
