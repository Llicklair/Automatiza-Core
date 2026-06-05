"""Migración de facturas históricas (import masivo desde otro programa).

Preserva número e importes, no encadena Verifactu ni genera asientos, y es
idempotente (emitidas por tipo+número; recibidas por tipo+número+proveedor).
"""

from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.billing import Invoice
from app.db.models.crm import Client
from app.db.models.models import Tenant
from app.services.migration.bulk_import import import_invoices_rows


async def _seed(db: AsyncSession):
    tenant = Tenant(id=uuid4(), name="MigInv S.L.", nif="B10101010", plan="starter")
    db.add(tenant)
    await db.flush()
    cli = Client(id=uuid4(), tenant_id=tenant.id, name="Cliente Histórico", nif="A20202020")
    db.add(cli)
    await db.flush()
    return tenant, cli


def _row(numero="A2023-0001", **over):
    base = {
        "numero": numero, "tipo": "issued", "nif": "A20202020",
        "fecha": "2023-05-14", "base": "1000", "iva": "210", "total": "1210",
    }
    base.update(over)
    return base


async def _count(db, tenant_id) -> int:
    r = await db.execute(select(func.count(Invoice.id)).where(Invoice.tenant_id == tenant_id))
    return int(r.scalar() or 0)


class TestInvoiceMigration:
    @pytest.mark.asyncio
    async def test_importa_preserva_numero_e_importes(self, db: AsyncSession):
        tenant, cli = await _seed(db)
        res = await import_invoices_rows([_row()], tenant.id, db)
        assert res.created == 1
        inv = (await db.execute(select(Invoice).where(Invoice.tenant_id == tenant.id))).scalars().first()
        assert inv.invoice_number == "A2023-0001"  # número de origen preservado
        assert float(inv.amount_base) == 1000.0
        assert float(inv.tax_amount) == 210.0
        assert float(inv.amount_total) == 1210.0
        assert inv.client_id == cli.id

    @pytest.mark.asyncio
    async def test_idempotente_emitida(self, db: AsyncSession):
        tenant, _ = await _seed(db)
        await import_invoices_rows([_row()], tenant.id, db)
        res2 = await import_invoices_rows([_row()], tenant.id, db)
        assert res2.created == 0
        assert res2.skipped == 1
        assert await _count(db, tenant.id) == 1

    @pytest.mark.asyncio
    async def test_total_derivado_de_base_mas_iva(self, db: AsyncSession):
        tenant, _ = await _seed(db)
        res = await import_invoices_rows([_row("A2023-0002", total="")], tenant.id, db)
        assert res.created == 1
        inv = (await db.execute(
            select(Invoice).where(Invoice.invoice_number == "A2023-0002")
        )).scalars().first()
        assert float(inv.amount_total) == 1210.0  # 1000 + 210

    @pytest.mark.asyncio
    async def test_cliente_inexistente_error(self, db: AsyncSession):
        tenant, _ = await _seed(db)
        res = await import_invoices_rows([_row(nif="Z99999999", cliente="Desconocido")], tenant.id, db)
        assert res.created == 0
        assert res.errors and "no encontrado" in res.errors[0]["reason"].lower()

    @pytest.mark.asyncio
    async def test_falta_numero_error(self, db: AsyncSession):
        tenant, _ = await _seed(db)
        res = await import_invoices_rows([_row(numero="")], tenant.id, db)
        assert res.created == 0
        assert res.errors
