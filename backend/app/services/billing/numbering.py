"""Numeración correlativa de facturas (FAC.NUM).

Cumple RD 1619/2012 Art. 6.1 — numeración correlativa por serie sin gaps.

Reutiliza la tabla `invoice_series` (modelo `InvoiceSeries`) que ya existe en
el esquema. Combina dos mecanismos para evitar colisiones de concurrencia:

* En PostgreSQL: ``pg_advisory_xact_lock`` por (tenant, serie, año) — bloquea
  cualquier otra transacción que intente emitir un número para la misma combo.
* Siempre: ``SELECT ... FOR UPDATE`` del row del counter (row-level lock).

El advisory lock es preferible porque bloquea desde el primer SQL de la
transacción y no requiere que la fila exista (caso "primera factura del año").
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.billing import InvoiceSeries


async def next_invoice_number(
    db: AsyncSession,
    tenant_id: UUID,
    series: str = "A",
    year: int | None = None,
) -> str:
    """Devuelve el siguiente número correlativo para (tenant, serie, año).

    Formato: ``{prefix}{year}-{NNNN}`` (ej. ``A2026-0001``). El prefix
    coincide con la serie salvo que el row tenga uno distinto persistido.

    El caller DEBE estar dentro de una transacción abierta. La función:
      1. Toma ``pg_advisory_xact_lock`` (en PostgreSQL).
      2. Hace ``SELECT ... FOR UPDATE`` del row de ``invoice_series``.
      3. Si no existe, lo crea con ``last_number=0``.
      4. Incrementa ``last_number`` y devuelve el número formateado.
    """
    if year is None:
        year = datetime.now(UTC).year

    dialect_name = db.bind.dialect.name if db.bind is not None else ""

    # Advisory lock — solo PostgreSQL. SQLite es single-writer por diseño.
    if dialect_name == "postgresql":
        lock_key = f"{tenant_id}:{series}:{year}"
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": lock_key},
        )

    result = await db.execute(
        select(InvoiceSeries)
        .where(
            InvoiceSeries.tenant_id == tenant_id,
            InvoiceSeries.serie == series,
            InvoiceSeries.year == year,
        )
        .with_for_update()
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = InvoiceSeries(
            tenant_id=tenant_id,
            serie=series,
            year=year,
            last_number=0,
            prefix=series,
        )
        db.add(row)
        await db.flush()

    row.last_number += 1
    await db.flush()
    return f"{row.prefix}{year}-{row.last_number:04d}"
