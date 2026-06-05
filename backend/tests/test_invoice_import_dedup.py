"""Idempotencia del import de facturas recibidas (anti-duplicado).

Una factura recibida se identifica por (proveedor, número del proveedor).
Reimportar el mismo borrador —p.ej. una automatización por evento que reescanee
la carpeta de documentos— NO debe crear una segunda factura. Este es el blindaje
que hace segura la asimilación documento→ERP.
"""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.billing import Invoice
from app.db.models.models import Tenant
from app.services.billing.invoice import delete_invoice
from app.services.billing.invoice_import import import_received_invoices


async def _seed_tenant(db: AsyncSession) -> Tenant:
    tenant = Tenant(id=uuid4(), name="Imp Corp S.L.", nif="B55667788", plan="starter")
    db.add(tenant)
    await db.flush()
    return tenant


def _draft(numero="PROV-2026-77"):
    return {
        "emisor": {"nif": "B12121212", "name": "Proveedor Uno S.L."},
        "invoice_number": numero,
        "issue_date": "2026-03-15",
        "amount_base": 100.0,
        "tax_amount": 21.0,
        "amount_total": 121.0,
        "lines": [
            {"description": "Material", "quantity": 1, "unit_price": 100.0,
             "tax_percentage": 21.0, "total": 121.0}
        ],
    }


async def _count_received(db, tenant_id) -> int:
    r = await db.execute(
        select(func.count(Invoice.id)).where(
            Invoice.tenant_id == tenant_id, Invoice.invoice_type == "received"
        )
    )
    return int(r.scalar() or 0)


class TestImportDedup:
    @pytest.mark.asyncio
    async def test_primera_importacion_crea(self, db: AsyncSession):
        tenant = await _seed_tenant(db)
        res = await import_received_invoices(db, tenant.id, [_draft()], uuid4())
        assert res[0]["ok"] is True
        assert not res[0].get("duplicate")
        assert await _count_received(db, tenant.id) == 1

    @pytest.mark.asyncio
    async def test_reimportar_mismo_no_duplica(self, db: AsyncSession):
        tenant = await _seed_tenant(db)
        uid = uuid4()
        await import_received_invoices(db, tenant.id, [_draft()], uid)
        # Segunda pasada del MISMO documento (lo que haría un reescaneo automático)
        res2 = await import_received_invoices(db, tenant.id, [_draft()], uid)
        assert res2[0]["ok"] is True
        assert res2[0].get("duplicate") is True
        assert res2[0].get("skipped") is True
        # Sigue habiendo UNA sola factura recibida.
        assert await _count_received(db, tenant.id) == 1

    @pytest.mark.asyncio
    async def test_distinto_numero_si_crea_segunda(self, db: AsyncSession):
        tenant = await _seed_tenant(db)
        uid = uuid4()
        await import_received_invoices(db, tenant.id, [_draft("PROV-A")], uid)
        await import_received_invoices(db, tenant.id, [_draft("PROV-B")], uid)
        assert await _count_received(db, tenant.id) == 2

    @pytest.mark.asyncio
    async def test_borrar_recibida_con_asiento_no_falla(self, db: AsyncSession):
        # Una recibida importada lleva asiento contable. Borrarla debe arrastrar
        # el asiento en cascada y no romper por la FK journal_entries.invoice_id.
        tenant = await _seed_tenant(db)
        res = await import_received_invoices(db, tenant.id, [_draft("DEL-1")], uuid4())
        inv_id = res[0]["invoice_id"]
        assert await _count_received(db, tenant.id) == 1

        ok = await delete_invoice(UUID(inv_id), tenant.id, db)
        assert ok is True
        assert await _count_received(db, tenant.id) == 0

    @pytest.mark.asyncio
    async def test_mismo_numero_distinto_proveedor_si_crea(self, db: AsyncSession):
        # El número de recibida lo pone el proveedor → mismo string en dos
        # proveedores distintos son dos facturas legítimas.
        tenant = await _seed_tenant(db)
        uid = uuid4()
        d1 = _draft("FRA-1")
        d2 = _draft("FRA-1")
        d2["emisor"] = {"nif": "B99999999", "name": "Proveedor Dos S.L."}
        await import_received_invoices(db, tenant.id, [d1], uid)
        await import_received_invoices(db, tenant.id, [d2], uid)
        assert await _count_received(db, tenant.id) == 2
