"""Seed de datos de ejemplo del onboarding (UI.ONB).

Siembra una pyme de ejemplo (clientes, productos, facturas) en el tenant del
usuario para que el producto "se vea vivo" en el trial (criterio de lanzamiento
SCOPE.md: dashboard no-vacío en <5 min). Todo lo sembrado lleva ``is_demo=True``:

  - **Visible** en listados y analítica (dashboard, /facturacion, /clientes…) —
    ese es justo el objetivo.
  - **Invisible** a TODA declaración fiscal: 303/130/390/347/libro registro
    excluyen ``Invoice.is_demo`` (ver services/reports/*). Las facturas demo NO
    consumen la serie correlativa real (numeración ``DEMO-NNNN``, sin pasar por
    ``next_invoice_number``).
  - **Borrable de golpe** con ``clear_demo_data`` ("Borrar datos de ejemplo").

Se construye DIRECTAMENTE (sin ``create_invoice``/``create_client``) a propósito:
el seed NO debe emitir eventos de negocio (dispararían workflows sobre datos
falsos) ni consumir la serie fiscal. Reutiliza
``compute_invoice_totals`` para los importes (misma aritmética Decimal validada).

Idempotente: si ya hay datos demo en el tenant, ``seed_demo_data`` no duplica.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import tenant_context
from app.db.models.crm import Client
from app.db.models.inventory import Product
from app.db.models.models import Invoice, InvoiceLine
from app.services.billing.queries import compute_invoice_totals
from app.services.onboarding.wizard import set_step

logger = logging.getLogger("onboarding.seed")

# Pyme de servicios genérica. Nombres con "(demo)" para que se reconozcan como
# ejemplo incluso sin badge. NIFs en un rango claramente ficticio.
_DEMO_CLIENTS: tuple[dict, ...] = (
    {
        "name": "Construcciones Vega SL (demo)",
        "nif": "B00000010",
        "email": "vega@ejemplo.test",
        "client_type": "customer",
        "city": "Madrid",
    },
    {
        "name": "Estudio Lúa SL (demo)",
        "nif": "B00000011",
        "email": "lua@ejemplo.test",
        "client_type": "customer",
        "city": "Valencia",
    },
    {
        "name": "Carmen Ruiz (demo)",
        "nif": "00000012Z",
        "email": "carmen@ejemplo.test",
        "client_type": "customer",
        "city": "Sevilla",
    },
    {
        "name": "Suministros Iberia SL (demo)",
        "nif": "B00000013",
        "email": "iberia@ejemplo.test",
        "client_type": "supplier",
        "city": "Bilbao",
    },
)

_DEMO_PRODUCTS: tuple[dict, ...] = (
    {
        "name": "Consultoría (hora) (demo)",
        "item_type": "service",
        "price": 60,
        "tax_percentage": 21,
        "stock_quantity": 0,
        "unit": "h",
    },
    {
        "name": "Mantenimiento mensual (demo)",
        "item_type": "service",
        "price": 250,
        "tax_percentage": 21,
        "stock_quantity": 0,
    },
    {"name": "Informe técnico (demo)", "item_type": "service", "price": 400, "tax_percentage": 21, "stock_quantity": 0},
    {
        "name": "Material de oficina (demo)",
        "item_type": "product",
        "price": 12.5,
        "tax_percentage": 21,
        "stock_quantity": 120,
    },
)


async def _demo_counts(db: AsyncSession, tenant_id: UUID) -> dict[str, int]:
    async def _count(model) -> int:
        res = await db.execute(
            select(func.count()).select_from(model).where(model.tenant_id == tenant_id, model.is_demo.is_(True))
        )
        return int(res.scalar() or 0)

    return {
        "clients": await _count(Client),
        "products": await _count(Product),
        "invoices": await _count(Invoice),
    }


async def _build_demo_invoice(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    number: str,
    invoice_type: str,
    client_id: UUID,
    lines_data: list[dict],
    date: datetime,
    status: str,
    due_date: datetime | None = None,
) -> Invoice:
    """Construye una factura demo + líneas SIN serie correlativa fiscal."""
    totals = compute_invoice_totals(lines_data)
    inv = Invoice(
        tenant_id=tenant_id,
        client_id=client_id,
        invoice_number=number,
        date=date,
        due_date=due_date,
        status=status,
        invoice_type=invoice_type,
        is_demo=True,
        amount_base=totals["amount_base"],
        tax_amount=totals["tax_amount"],
        amount_total=totals["amount_total"],
    )
    db.add(inv)
    await db.flush()  # poblar inv.id para las líneas (atómico, sin commit)
    for ld in totals["lines"]:
        db.add(
            InvoiceLine(
                invoice_id=inv.id,
                product_id=ld.get("product_id"),
                description=ld.get("description"),
                quantity=ld["quantity"],
                unit_price=ld["unit_price"],
                discount_percentage=ld["discount_percentage"],
                tax_percentage=ld["tax_percentage"],
                total=ld["_line_total"],
            )
        )
    return inv


async def seed_demo_data(db: AsyncSession, *, tenant_id: UUID, user_id: UUID) -> dict:
    """Siembra la pyme de ejemplo en el tenant. Idempotente.

    Devuelve ``{"already_seeded": bool, "clients": int, "products": int,
    "invoices": int}``.
    """
    with tenant_context(str(tenant_id)):
        existing = await _demo_counts(db, tenant_id)
        if any(existing.values()):
            return {"already_seeded": True, **existing}

        clients = [Client(tenant_id=tenant_id, is_demo=True, **c) for c in _DEMO_CLIENTS]
        products = [Product(tenant_id=tenant_id, is_demo=True, **p) for p in _DEMO_PRODUCTS]
        db.add_all(clients)
        db.add_all(products)
        await db.flush()  # poblar ids de clientes/productos

        now = datetime.now(UTC)

        def _line(prod: Product, qty: float) -> dict:
            return {
                "product_id": prod.id,
                "description": prod.name,
                "quantity": qty,
                "unit_price": float(prod.price),
                "discount_percentage": 0.0,
                "tax_percentage": float(prod.tax_percentage or 21),
            }

        # Facturas EMITIDAS demo (serie no fiscal "DEMO-"), repartidas en el
        # tiempo para que el dashboard tenga una curva. Casi todas "paid" (no
        # morosas → no disparan recordatorios de cobro sobre datos falsos).
        await _build_demo_invoice(
            db,
            tenant_id=tenant_id,
            number="DEMO-0001",
            invoice_type="issued",
            client_id=clients[0].id,
            lines_data=[_line(products[0], 10)],
            date=now - timedelta(days=92),
            status="paid",
        )
        await _build_demo_invoice(
            db,
            tenant_id=tenant_id,
            number="DEMO-0002",
            invoice_type="issued",
            client_id=clients[1].id,
            lines_data=[_line(products[1], 1), _line(products[3], 5)],
            date=now - timedelta(days=61),
            status="paid",
        )
        await _build_demo_invoice(
            db,
            tenant_id=tenant_id,
            number="DEMO-0003",
            invoice_type="issued",
            client_id=clients[2].id,
            lines_data=[_line(products[2], 1)],
            date=now - timedelta(days=30),
            status="paid",
        )
        await _build_demo_invoice(
            db,
            tenant_id=tenant_id,
            number="DEMO-0004",
            invoice_type="issued",
            client_id=clients[0].id,
            lines_data=[_line(products[1], 1)],
            date=now - timedelta(days=8),
            status="pending",
            due_date=now + timedelta(days=22),
        )
        # Una factura RECIBIDA (proveedor) para que "gastos" no salga a cero.
        await _build_demo_invoice(
            db,
            tenant_id=tenant_id,
            number="PROV-DEMO-0001",
            invoice_type="received",
            client_id=clients[3].id,
            lines_data=[
                {
                    "description": "Suministros varios (demo)",
                    "quantity": 1,
                    "unit_price": 180.0,
                    "discount_percentage": 0.0,
                    "tax_percentage": 21,
                }
            ],
            date=now - timedelta(days=40),
            status="paid",
        )

        await db.flush()
        # Marca el paso "tengo datos" del wizard.
        await set_step(db, tenant_id=tenant_id, step="data", value=True)
        await db.commit()

        counts = await _demo_counts(db, tenant_id)
        logger.info("Seed demo sembrado para tenant %s: %s", tenant_id, counts)
        return {"already_seeded": False, **counts}


async def clear_demo_data(db: AsyncSession, *, tenant_id: UUID) -> dict:
    """Borra TODOS los datos demo del tenant. Devuelve ``{"deleted": {...}}``.

    Orden por FK: facturas (líneas por cascade ORM) → productos → clientes.
    """
    with tenant_context(str(tenant_id)):
        counts = await _demo_counts(db, tenant_id)

        # Facturas: delete por objeto para que el cascade ORM borre las líneas.
        inv_res = await db.execute(select(Invoice).where(Invoice.tenant_id == tenant_id, Invoice.is_demo.is_(True)))
        for inv in inv_res.scalars().all():
            await db.delete(inv)
        await db.flush()

        await db.execute(delete(Product).where(Product.tenant_id == tenant_id, Product.is_demo.is_(True)))
        await db.execute(delete(Client).where(Client.tenant_id == tenant_id, Client.is_demo.is_(True)))
        await db.commit()
        logger.info("Datos demo borrados para tenant %s: %s", tenant_id, counts)
        return {"deleted": counts}


async def demo_status(db: AsyncSession, *, tenant_id: UUID) -> dict:
    """Devuelve ``{"seeded": bool, "counts": {...}}``."""
    with tenant_context(str(tenant_id)):
        counts = await _demo_counts(db, tenant_id)
    return {"seeded": any(counts.values()), "counts": counts}
