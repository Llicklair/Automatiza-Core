"""Tests de facturas rectificativas por anulación (RD 1619/2012 Art. 15).

`create_rectificativa` emite una nueva factura que minora íntegramente a la
original con importes negados, vinculada a ella y con su motivo, numeración
correlativa propia (serie R) y encadenado Verifactu. Es un hecho con efectos
fiscales, por lo que se valida el camino del dinero de extremo a extremo.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import Client, Invoice, Tenant
from app.db.models.billing import InvoiceLine
from app.services.billing.invoice import create_invoice, create_rectificativa


async def _seed(db: AsyncSession):
    tenant = Tenant(id=uuid4(), name="Rect Corp S.L.", nif="B12345678", plan="starter")
    db.add(tenant)
    await db.flush()
    client = Client(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Cliente",
        nif="A11223344",
        email="c@test.com",
    )
    db.add(client)
    await db.flush()
    return tenant, client


async def _original(db, tenant, client):
    payload = {"date": datetime.now(UTC), "status": "pending"}
    lines = [
        {"description": "Servicio", "quantity": 2, "unit_price": 100.0, "tax_percentage": 21.0},
        {"description": "Material", "quantity": 1, "unit_price": 50.0, "tax_percentage": 10.0},
    ]
    return await create_invoice(client.id, payload, lines, tenant.id, uuid4(), db)


@pytest.mark.asyncio
async def test_barrera_bd_una_rectificativa_por_original(db: AsyncSession):
    """La BARRERA de BD (uq_invoices_rectifies_once), no solo el guard de app:
    dos rectificativas con el mismo rectifies_invoice_id chocan al flush.

    Inserta directamente (saltando create_rectificativa) como haría una carrera
    concurrente que pasa el SELECT-then-insert a la vez → IntegrityError.
    """
    tenant, client = await _seed(db)
    orig = await _original(db, tenant, client)

    def _rect(num: str) -> Invoice:
        return Invoice(
            id=uuid4(),
            tenant_id=tenant.id,
            client_id=client.id,
            invoice_number=num,
            date=datetime.now(UTC),
            status="pending",
            invoice_type="rectificativa",
            rectifies_invoice_id=orig.id,
            amount_base=Decimal("-1"),
            amount_total=Decimal("-1"),
        )

    db.add(_rect("R-A"))
    await db.flush()
    db.add(_rect("R-B"))
    with pytest.raises(IntegrityError):
        await db.flush()
    await db.rollback()


class TestCreateRectificativa:
    @pytest.mark.asyncio
    async def test_importes_negados(self, db: AsyncSession):
        tenant, client = await _seed(db)
        orig = await _original(db, tenant, client)

        rect = await create_rectificativa(orig.id, "Anulación por error", tenant.id, db)

        # base 200+50=250, iva 42+5=47, total 297 → la rectificativa los niega.
        assert float(rect.amount_base) == -float(orig.amount_base)
        assert float(rect.tax_amount) == -float(orig.tax_amount)
        assert float(rect.amount_total) == -float(orig.amount_total)
        # El neto con la original queda a cero.
        assert float(orig.amount_total) + float(rect.amount_total) == 0.0

    @pytest.mark.asyncio
    async def test_tipo_vinculo_y_motivo(self, db: AsyncSession):
        tenant, client = await _seed(db)
        orig = await _original(db, tenant, client)

        rect = await create_rectificativa(orig.id, "Cliente desiste", tenant.id, db)

        assert rect.invoice_type == "rectificativa"
        assert rect.rectifies_invoice_id == orig.id
        assert rect.rectification_reason == "Cliente desiste"

    @pytest.mark.asyncio
    async def test_numeracion_serie_r(self, db: AsyncSession):
        tenant, client = await _seed(db)
        orig = await _original(db, tenant, client)

        rect = await create_rectificativa(orig.id, "motivo", tenant.id, db)
        assert rect.invoice_number.startswith("R")
        assert rect.invoice_number != orig.invoice_number

    @pytest.mark.asyncio
    async def test_lineas_espejo_negadas(self, db: AsyncSession):
        tenant, client = await _seed(db)
        orig = await _original(db, tenant, client)

        rect = await create_rectificativa(orig.id, "motivo", tenant.id, db)

        res = await db.execute(select(InvoiceLine).where(InvoiceLine.invoice_id == rect.id))
        rect_lines = res.scalars().all()
        assert len(rect_lines) == 2
        for ln in rect_lines:
            assert float(ln.total) < 0

    @pytest.mark.asyncio
    async def test_idempotencia_no_doble_abono(self, db: AsyncSession):
        tenant, client = await _seed(db)
        orig = await _original(db, tenant, client)

        await create_rectificativa(orig.id, "motivo", tenant.id, db)
        with pytest.raises(ValueError, match="Ya existe una factura rectificativa"):
            await create_rectificativa(orig.id, "otra vez", tenant.id, db)

    @pytest.mark.asyncio
    async def test_motivo_obligatorio(self, db: AsyncSession):
        tenant, client = await _seed(db)
        orig = await _original(db, tenant, client)
        with pytest.raises(ValueError, match="motivo"):
            await create_rectificativa(orig.id, "   ", tenant.id, db)

    @pytest.mark.asyncio
    async def test_original_inexistente(self, db: AsyncSession):
        tenant, _ = await _seed(db)
        with pytest.raises(ValueError, match="no encontrada"):
            await create_rectificativa(uuid4(), "motivo", tenant.id, db)

    @pytest.mark.asyncio
    async def test_no_rectificar_una_rectificativa(self, db: AsyncSession):
        tenant, client = await _seed(db)
        orig = await _original(db, tenant, client)
        rect = await create_rectificativa(orig.id, "motivo", tenant.id, db)
        with pytest.raises(ValueError, match="rectificativa"):
            await create_rectificativa(rect.id, "motivo", tenant.id, db)
