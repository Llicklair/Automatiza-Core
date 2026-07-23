"""T7 tintorería: facturación agrupada de albaranes (N:M factura ↔ albarán).

N albaranes del MISMO cliente → UNA factura borrador con las líneas de todos
(prefijadas con el nº de albarán) y enlaces que impiden el doble cobro.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db.models.billing import DeliveryNote, DeliveryNoteLine, InvoiceDeliveryNote, InvoiceLine
from app.db.models.crm import Client
from app.services.sales.commands import facturar_albaranes
from app.services.sales.queries import list_albaranes


async def _albaran(db, tenant_id, client_id, *, numero, total="12.10", status="delivered"):
    note = DeliveryNote(
        tenant_id=tenant_id,
        client_id=client_id,
        albaran_number=numero,
        date=datetime(2026, 7, 20, tzinfo=UTC).date(),
        status=status,
        amount_base=Decimal("10.00"),
        tax_amount=Decimal("2.10"),
        amount_total=Decimal(total),
    )
    db.add(note)
    await db.flush()
    db.add(
        DeliveryNoteLine(
            albaran_id=note.id,
            description="Limpieza traje",
            quantity=Decimal("1"),
            unit_price=Decimal("10.00"),
            tax_percentage=Decimal("21.00"),
            total=Decimal(total),
        )
    )
    await db.flush()
    return note


async def _cliente(db, tenant_id, name="Hotel Sol SL"):
    # NIF único por nombre: la tabla tiene unique(tenant_id, nif).
    nif = f"B{abs(hash(name)) % 10**8:08d}"
    cli = Client(tenant_id=tenant_id, name=name, nif=nif, phone="612 345 678")
    db.add(cli)
    await db.flush()
    return cli


@pytest.mark.asyncio
class TestFacturarAlbaranes:
    async def test_agrupa_dos_albaranes_en_una_factura_borrador(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        cli = await _cliente(db, tenant.id)
        a1 = await _albaran(db, tenant.id, cli.id, numero="ALB-001")
        a2 = await _albaran(db, tenant.id, cli.id, numero="ALB-002")
        await db.commit()

        invoice = await facturar_albaranes([a1.id, a2.id], tenant.id, db, user_id=user.id)

        assert invoice.status == "draft"  # se revisa y emite desde Facturas
        assert float(invoice.amount_total) == pytest.approx(24.20)
        lines = (await db.execute(select(InvoiceLine).where(InvoiceLine.invoice_id == invoice.id))).scalars().all()
        assert len(lines) == 2
        descs = sorted(str(ln.description) for ln in lines)
        assert descs[0].startswith("[ALB-001]")
        assert descs[1].startswith("[ALB-002]")
        links = (
            (await db.execute(select(InvoiceDeliveryNote).where(InvoiceDeliveryNote.invoice_id == invoice.id)))
            .scalars()
            .all()
        )
        assert {link.albaran_id for link in links} == {a1.id, a2.id}

        # El listado expone los enlaces (badge "Facturado" en el frontend)
        # y los datos del cliente para el buscador por nombre/NIF/teléfono (T4).
        listado = await list_albaranes(tenant.id, db)
        por_num = {n.albaran_number: n for n in listado}
        assert por_num["ALB-001"].invoice_ids == [invoice.id]
        assert por_num["ALB-001"].client_name == "Hotel Sol SL"
        assert por_num["ALB-001"].client_nif == cli.nif
        assert por_num["ALB-001"].client_phone == "612 345 678"

    async def test_clientes_distintos_rechazado(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        c1 = await _cliente(db, tenant.id, "Hotel A")
        c2 = await _cliente(db, tenant.id, "Hotel B")
        a1 = await _albaran(db, tenant.id, c1.id, numero="ALB-010")
        a2 = await _albaran(db, tenant.id, c2.id, numero="ALB-011")
        await db.commit()

        with pytest.raises(ValueError, match="mismo cliente"):
            await facturar_albaranes([a1.id, a2.id], tenant.id, db, user_id=user.id)

    async def test_anulado_rechazado(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        cli = await _cliente(db, tenant.id)
        a1 = await _albaran(db, tenant.id, cli.id, numero="ALB-020", status="anulado")
        await db.commit()

        with pytest.raises(ValueError, match="anulado"):
            await facturar_albaranes([a1.id], tenant.id, db, user_id=user.id)

    async def test_doble_cobro_bloqueado(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        cli = await _cliente(db, tenant.id)
        a1 = await _albaran(db, tenant.id, cli.id, numero="ALB-030")
        await db.commit()

        await facturar_albaranes([a1.id], tenant.id, db, user_id=user.id)
        with pytest.raises(ValueError, match="ya está facturado"):
            await facturar_albaranes([a1.id], tenant.id, db, user_id=user.id)

    async def test_sin_cliente_rechazado(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        a1 = await _albaran(db, tenant.id, None, numero="ALB-040")
        await db.commit()

        with pytest.raises(ValueError, match="cliente asignado"):
            await facturar_albaranes([a1.id], tenant.id, db, user_id=user.id)
