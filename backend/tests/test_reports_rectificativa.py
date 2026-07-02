"""Los ingresos del informe de gestión netean las rectificativas.

Bug de origen (audit UX 2026-07-02, P1-1): reports/aggregation.py contaba solo
`invoice_type == "issued"` mientras analytics usaba el conjunto canónico
issued+rectificativa — el mismo mes daba dos cifras de ingresos distintas en
Informes y Analítica. La definición única vive en billing/constants.py
(EMITTED_INVOICE_TYPES) y este test fija la semántica: neto de abonos.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.db.base import AsyncSessionLocal
from app.db.models.models import Client, Invoice, Tenant
from app.services.reports.aggregation import aggregate


async def _seed_tenant_with_rectificativa() -> UUID:
    async with AsyncSessionLocal() as db:
        tenant = Tenant(
            id=uuid4(), name="Informes S.L.", nif=f"B{str(uuid4().int)[:8]}", plan="starter"
        )
        db.add(tenant)
        await db.flush()
        client = Client(id=uuid4(), tenant_id=tenant.id, name="Cliente", nif="B87654321")
        db.add(client)
        await db.flush()
        common = {"tenant_id": tenant.id, "client_id": client.id, "status": "paid"}
        db.add(
            Invoice(
                id=uuid4(),
                invoice_number="FAC-1",
                date=datetime(2026, 5, 10, tzinfo=UTC),
                amount_base=Decimal("1000"),
                tax_amount=Decimal("210"),
                amount_total=Decimal("1210"),
                invoice_type="issued",
                **common,
            )
        )
        db.add(
            Invoice(
                id=uuid4(),
                invoice_number="R-2026-0001",
                date=datetime(2026, 5, 20, tzinfo=UTC),
                amount_base=Decimal("-200"),
                tax_amount=Decimal("-42"),
                amount_total=Decimal("-242"),
                invoice_type="rectificativa",
                **common,
            )
        )
        await db.commit()
        return tenant.id


async def test_ingresos_del_informe_netean_rectificativas():
    tid = await _seed_tenant_with_rectificativa()
    async with AsyncSessionLocal() as db:
        snap = await aggregate(db, tid, date(2026, 5, 1), date(2026, 5, 31))
    # 1210 emitida − 242 abono = 968 neto (misma cifra que muestra Analítica).
    assert snap.facturas.ingresos_total == 968.0
    # La rectificativa cuenta como documento emitido (cadena de facturación).
    assert snap.facturas.facturas_emitidas == 2
