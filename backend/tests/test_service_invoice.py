"""Tests para app.services.billing.invoice — CRUD de facturas."""
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import Client, Invoice, Tenant
from app.services.billing.invoice import (
    VALID_IVA,
    create_invoice,
    delete_invoice,
    get_invoice,
    list_invoices,
    update_status,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _seed_tenant_client(db: AsyncSession):
    """Create a tenant and client for invoice tests."""
    tenant = Tenant(
        id=uuid4(),
        name="Test Corp S.L.",
        nif="B99887766",
        plan="starter",
    )
    db.add(tenant)
    await db.flush()

    client = Client(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Cliente Test",
        nif="A11223344",
        email="cliente@test.com",
    )
    db.add(client)
    await db.flush()
    return tenant, client


async def _create_basic_invoice(db, tenant, client, user_id=None, **extra):
    """Shortcut to create one invoice with a single line."""
    uid = user_id or uuid4()
    payload = {
        "date": datetime.now(timezone.utc),
        "status": "draft",
        **extra,
    }
    lines = [
        {
            "description": "Servicio de consultoría",
            "quantity": 2,
            "unit_price": 100.0,
            "tax_percentage": 21.0,
        }
    ]
    return await create_invoice(client.id, payload, lines, tenant.id, uid, db)


# ── Tests ────────────────────────────────────────────────────────────────────


class TestValidIva:
    def test_valid_iva_values(self):
        assert VALID_IVA == {0.0, 4.0, 10.0, 21.0}


class TestCreateInvoice:
    @pytest.mark.asyncio
    async def test_create_invoice_basic(self, db: AsyncSession):
        tenant, client = await _seed_tenant_client(db)
        invoice = await _create_basic_invoice(db, tenant, client)

        assert invoice is not None
        assert invoice.tenant_id == tenant.id
        assert invoice.client_id == client.id
        assert invoice.invoice_number is not None

    @pytest.mark.asyncio
    async def test_invoice_amounts_calculated(self, db: AsyncSession):
        tenant, client = await _seed_tenant_client(db)
        invoice = await _create_basic_invoice(db, tenant, client)

        # 2 * 100 = 200 base, 21% tax = 42, total = 242
        assert float(invoice.amount_base) == 200.0
        assert float(invoice.tax_amount) == 42.0
        assert float(invoice.amount_total) == 242.0

    @pytest.mark.asyncio
    async def test_invoice_with_discount(self, db: AsyncSession):
        tenant, client = await _seed_tenant_client(db)
        uid = uuid4()
        payload = {"date": datetime.now(timezone.utc), "status": "draft"}
        lines = [
            {
                "description": "Producto con descuento",
                "quantity": 1,
                "unit_price": 100.0,
                "discount_percentage": 10.0,
                "tax_percentage": 21.0,
            }
        ]
        invoice = await create_invoice(client.id, payload, lines, tenant.id, uid, db)

        # base = 100 - 10% = 90, tax = 90*0.21 = 18.9, total = 108.9
        assert float(invoice.amount_base) == 90.0
        assert float(invoice.tax_amount) == 18.9
        assert float(invoice.amount_total) == 108.9

    @pytest.mark.asyncio
    async def test_invoice_with_zero_iva(self, db: AsyncSession):
        tenant, client = await _seed_tenant_client(db)
        uid = uuid4()
        payload = {"date": datetime.now(timezone.utc), "status": "draft"}
        lines = [
            {
                "description": "Producto exento",
                "quantity": 1,
                "unit_price": 50.0,
                "tax_percentage": 0.0,
            }
        ]
        invoice = await create_invoice(client.id, payload, lines, tenant.id, uid, db)
        assert float(invoice.tax_amount) == 0.0
        assert float(invoice.amount_total) == 50.0

    @pytest.mark.asyncio
    async def test_invoice_invalid_iva_raises(self, db: AsyncSession):
        tenant, client = await _seed_tenant_client(db)
        uid = uuid4()
        payload = {"date": datetime.now(timezone.utc), "status": "draft"}
        lines = [
            {
                "description": "Producto",
                "quantity": 1,
                "unit_price": 100.0,
                "tax_percentage": 15.0,  # invalid
            }
        ]
        with pytest.raises(ValueError, match="IVA inválido"):
            await create_invoice(client.id, payload, lines, tenant.id, uid, db)

    @pytest.mark.asyncio
    async def test_invoice_manual_number(self, db: AsyncSession):
        tenant, client = await _seed_tenant_client(db)
        uid = uuid4()
        payload = {
            "date": datetime.now(timezone.utc),
            "status": "draft",
            "invoice_number": "MANUAL-001",
        }
        lines = [
            {"description": "Test", "quantity": 1, "unit_price": 10.0, "tax_percentage": 21.0}
        ]
        invoice = await create_invoice(client.id, payload, lines, tenant.id, uid, db)
        assert invoice.invoice_number == "MANUAL-001"

    @pytest.mark.asyncio
    async def test_invoice_auto_number_with_series(self, db: AsyncSession):
        tenant, client = await _seed_tenant_client(db)
        invoice = await _create_basic_invoice(db, tenant, client)
        assert invoice.invoice_number.startswith("F")

    @pytest.mark.asyncio
    async def test_invoice_strips_frontend_totals(self, db: AsyncSession):
        """amount_base, tax_amount, amount_total in payload are ignored."""
        tenant, client = await _seed_tenant_client(db)
        uid = uuid4()
        payload = {
            "date": datetime.now(timezone.utc),
            "status": "draft",
            "amount_base": 9999.0,
            "tax_amount": 9999.0,
            "amount_total": 9999.0,
        }
        lines = [
            {"description": "Test", "quantity": 1, "unit_price": 100.0, "tax_percentage": 21.0}
        ]
        invoice = await create_invoice(client.id, payload, lines, tenant.id, uid, db)
        # Should be calculated, not the 9999 values
        assert float(invoice.amount_total) == 121.0


class TestListInvoices:
    @pytest.mark.asyncio
    async def test_list_empty(self, db: AsyncSession):
        tenant, _ = await _seed_tenant_client(db)
        result = await list_invoices(tenant.id, db)
        assert result == []

    @pytest.mark.asyncio
    async def test_list_with_invoices(self, db: AsyncSession):
        tenant, client = await _seed_tenant_client(db)
        await _create_basic_invoice(db, tenant, client)
        await _create_basic_invoice(db, tenant, client)

        result = await list_invoices(tenant.id, db)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_pagination(self, db: AsyncSession):
        tenant, client = await _seed_tenant_client(db)
        for _ in range(3):
            await _create_basic_invoice(db, tenant, client)

        result = await list_invoices(tenant.id, db, skip=0, limit=2)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_tenant_isolation(self, db: AsyncSession):
        """Invoices from another tenant should not appear."""
        tenant1, client1 = await _seed_tenant_client(db)
        tenant2 = Tenant(id=uuid4(), name="Other Corp", nif="B00000001", plan="starter")
        db.add(tenant2)
        await db.flush()

        await _create_basic_invoice(db, tenant1, client1)
        result = await list_invoices(tenant2.id, db)
        assert result == []


class TestGetInvoice:
    @pytest.mark.asyncio
    async def test_get_existing(self, db: AsyncSession):
        tenant, client = await _seed_tenant_client(db)
        created = await _create_basic_invoice(db, tenant, client)

        fetched = await get_invoice(created.id, tenant.id, db)
        assert fetched is not None
        assert fetched.id == created.id

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, db: AsyncSession):
        tenant, _ = await _seed_tenant_client(db)
        result = await get_invoice(uuid4(), tenant.id, db)
        assert result is None


class TestUpdateStatus:
    @pytest.mark.asyncio
    async def test_update_to_paid(self, db: AsyncSession):
        tenant, client = await _seed_tenant_client(db)
        invoice = await _create_basic_invoice(db, tenant, client)

        updated = await update_status(invoice.id, tenant.id, "paid", db)
        assert updated.status == "paid"

    @pytest.mark.asyncio
    async def test_update_invalid_status_raises(self, db: AsyncSession):
        tenant, client = await _seed_tenant_client(db)
        invoice = await _create_basic_invoice(db, tenant, client)

        with pytest.raises(ValueError, match="Estado no válido"):
            await update_status(invoice.id, tenant.id, "invalid_status", db)

    @pytest.mark.asyncio
    async def test_update_nonexistent_raises(self, db: AsyncSession):
        tenant, _ = await _seed_tenant_client(db)
        with pytest.raises(ValueError, match="Factura no encontrada"):
            await update_status(uuid4(), tenant.id, "paid", db)


class TestDeleteInvoice:
    @pytest.mark.asyncio
    async def test_delete_existing(self, db: AsyncSession):
        tenant, client = await _seed_tenant_client(db)
        invoice = await _create_basic_invoice(db, tenant, client)

        result = await delete_invoice(invoice.id, tenant.id, db)
        assert result is True

        fetched = await get_invoice(invoice.id, tenant.id, db)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, db: AsyncSession):
        tenant, _ = await _seed_tenant_client(db)
        result = await delete_invoice(uuid4(), tenant.id, db)
        assert result is False
