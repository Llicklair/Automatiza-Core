"""T8 tintorería: edición de albaranes no cerrados.

Editable: líneas/notas/fecha/cliente mientras el albarán no esté entregado,
anulado ni facturado. Confirmado (stock ya descontado) no admite cambio de
líneas. El cliente se resuelve por nombre (find-or-create, alta exprés).
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.db.models.billing import DeliveryNote, DeliveryNoteLine
from app.db.models.crm import Client
from app.services.sales.commands import create_albaran, facturar_albaranes, update_albaran


def _linea(desc="Limpieza abrigo", qty=1, price=15, tax=21, product_id=None):
    return SimpleNamespace(product_id=product_id, description=desc, quantity=qty, unit_price=price, tax_percentage=tax)


async def _albaran(db, tenant_id, *, status="recibido", client_id=None):
    note = DeliveryNote(
        tenant_id=tenant_id,
        client_id=client_id,
        albaran_number=f"ALB-T8-{abs(hash((str(tenant_id), status))) % 10**6}",
        date=datetime(2026, 7, 20, tzinfo=UTC).date(),
        status=status,
        amount_base=Decimal("10.00"),
        tax_amount=Decimal("2.10"),
        amount_total=Decimal("12.10"),
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
            total=Decimal("12.10"),
        )
    )
    await db.commit()
    return note


@pytest.mark.asyncio
class TestUpdateAlbaran:
    async def test_edita_lineas_y_recalcula_totales(self, db, seed_tenant_and_user):
        tenant, _user, _t = seed_tenant_and_user
        note = await _albaran(db, tenant.id)

        updated = await update_albaran(
            note.id,
            tenant.id,
            db,
            notes="Mancha de vino en solapa",
            lines=[_linea(qty=2, price=15), _linea("Plancha camisa", qty=3, price=2)],
        )

        assert updated.notes == "Mancha de vino en solapa"
        assert len(updated.lines) == 2
        # 2*15 + 3*2 = 36 base; 21% → 43.56 total
        assert float(updated.amount_total) == pytest.approx(43.56)

    async def test_entregado_no_editable(self, db, seed_tenant_and_user):
        tenant, _user, _t = seed_tenant_and_user
        note = await _albaran(db, tenant.id, status="delivered")
        with pytest.raises(ValueError, match="rectificación"):
            await update_albaran(note.id, tenant.id, db, notes="tarde")

    async def test_facturado_no_editable(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        cli = Client(tenant_id=tenant.id, name="Hotel T8", nif="B00000088")
        db.add(cli)
        await db.flush()
        note = await _albaran(db, tenant.id, status="delivered", client_id=cli.id)
        note.status = "listo"  # facturable pero editable si no tuviera factura
        await db.commit()
        await facturar_albaranes([note.id], tenant.id, db, user_id=user.id)

        with pytest.raises(ValueError, match="facturado"):
            await update_albaran(note.id, tenant.id, db, notes="tarde")

    async def test_confirmado_bloquea_lineas_pero_permite_notas(self, db, seed_tenant_and_user):
        tenant, _user, _t = seed_tenant_and_user
        note = await _albaran(db, tenant.id, status="confirmed")

        with pytest.raises(ValueError, match="borrador"):
            await update_albaran(note.id, tenant.id, db, lines=[_linea()])

        updated = await update_albaran(note.id, tenant.id, db, notes="urgente")
        assert updated.notes == "urgente"

    async def test_cliente_por_nombre_find_or_create_y_limpiar(self, db, seed_tenant_and_user):
        tenant, _user, _t = seed_tenant_and_user
        note = await _albaran(db, tenant.id)

        # Nombre nuevo → alta exprés
        updated = await update_albaran(note.id, tenant.id, db, client_name="Pascual Tintorería")
        creado = (
            (await db.execute(select(Client).where(Client.tenant_id == tenant.id, Client.name == "Pascual Tintorería")))
            .scalars()
            .one()
        )
        assert updated.client_id == creado.id

        # Mismo nombre (otra capitalización) → reutiliza, no duplica
        updated = await update_albaran(note.id, tenant.id, db, client_name="pascual tintorería")
        assert updated.client_id == creado.id

        # Cadena vacía → desenlaza
        updated = await update_albaran(note.id, tenant.id, db, client_name="")
        assert updated.client_id is None

    async def test_sin_lineas_rechazado(self, db, seed_tenant_and_user):
        tenant, _user, _t = seed_tenant_and_user
        note = await _albaran(db, tenant.id)
        with pytest.raises(ValueError, match="al menos una línea"):
            await update_albaran(note.id, tenant.id, db, lines=[])

    async def test_create_con_client_name_enlaza_cliente(self, db, seed_tenant_and_user):
        # El campo "cliente" del modal de creación antes se ignoraba en silencio.
        tenant, _user, _t = seed_tenant_and_user
        note = await create_albaran(tenant.id, None, date(2026, 7, 22), None, [_linea()], db, client_name="Bar Manolo")
        assert note.client_id is not None
