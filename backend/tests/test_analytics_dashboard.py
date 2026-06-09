"""El dashboard de analítica abre por defecto en el último mes CON datos.

Bug observado: el frontend pedía el mes natural en curso; si no había facturas
ese mes (típico a principio de mes), el dashboard salía a cero aunque hubiera
datos en meses anteriores. Fix: sin periodo explícito, el backend usa el último
mes con facturas (latest_period_with_data); fallback al mes actual si no hay.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.db.base import AsyncSessionLocal
from app.db.models.models import Client, Invoice, Tenant
from app.services.analytics import latest_period_with_data


async def _seed_tenant(invoice_dt: datetime | None) -> UUID:
    async with AsyncSessionLocal() as db:
        tenant = Tenant(
            id=uuid4(), name="Analítica S.L.", nif=f"B{str(uuid4().int)[:8]}", plan="starter"
        )
        db.add(tenant)
        await db.flush()
        if invoice_dt is not None:
            client = Client(id=uuid4(), tenant_id=tenant.id, name="Cliente", nif="B12345678")
            db.add(client)
            await db.flush()
            db.add(
                Invoice(
                    id=uuid4(),
                    tenant_id=tenant.id,
                    client_id=client.id,
                    invoice_number="FAC-1",
                    date=invoice_dt,
                    amount_base=Decimal("100"),
                    tax_amount=Decimal("21"),
                    amount_total=Decimal("121"),
                    status="draft",
                    invoice_type="issued",
                )
            )
        await db.commit()
        return tenant.id


async def test_latest_period_returns_month_of_last_invoice():
    tid = await _seed_tenant(datetime(2025, 3, 10, tzinfo=UTC))
    async with AsyncSessionLocal() as db:
        assert await latest_period_with_data(db, tid) == "2025-03"


async def test_latest_period_none_when_no_invoices():
    tid = await _seed_tenant(None)
    async with AsyncSessionLocal() as db:
        assert await latest_period_with_data(db, tid) is None


# NOTA: no se testea get_dashboard() de extremo a extremo aquí porque usa SQL
# exclusivo de Postgres (extract('isodow', …)) que no compila en el SQLite de
# los tests. El default de la ruta se construye sobre latest_period_with_data
# (cubierto arriba) + el parse_month ya testeado; verificado además contra la
# DB real (último mes con datos = 2025-05 para el tenant AutomatizaCore).
