"""Tests para app.services.billing.invoice — CRUD de facturas."""
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from app.db.models.models import Client, Invoice, Tenant
from app.services.billing.invoice import (
    VALID_IVA,
    create_invoice,
    delete_invoice,
    get_invoice,
    list_invoices,
    update_status,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

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
        "date": datetime.now(UTC),
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
        assert invoice.invoice_number is None  # PROFORMA: sin número fiscal
        assert invoice.invoice_type == "proforma"

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
        payload = {"date": datetime.now(UTC), "status": "draft"}
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
        payload = {"date": datetime.now(UTC), "status": "draft"}
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
        payload = {"date": datetime.now(UTC), "status": "draft"}
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
    async def test_manual_number_ignored_for_proforma(self, db: AsyncSession):
        """El número manual se ignora: una emisión propia se degrada a PROFORMA
        sin número (solo las recibidas conservan el número externo)."""
        tenant, client = await _seed_tenant_client(db)
        uid = uuid4()
        payload = {
            "date": datetime.now(UTC),
            "status": "draft",
            "invoice_number": "MANUAL-001",
        }
        lines = [
            {"description": "Test", "quantity": 1, "unit_price": 10.0, "tax_percentage": 21.0}
        ]
        invoice = await create_invoice(client.id, payload, lines, tenant.id, uid, db)
        assert invoice.invoice_number is None
        assert invoice.invoice_type == "proforma"

    @pytest.mark.asyncio
    async def test_duplicate_issued_number_blocked_by_db(self, db: AsyncSession):
        """El índice único parcial (tenant, número) sobre facturas EMITIDAS
        (issued/rectificativa) sigue vigente. create_invoice ya no las produce
        (degrada a proforma), así que se insertan directamente como haría una
        importación o una carrera concurrente → IntegrityError."""
        tenant, client = await _seed_tenant_client(db)

        def _issued(num: str) -> Invoice:
            return Invoice(
                id=uuid4(), tenant_id=tenant.id, client_id=client.id,
                invoice_number=num, date=datetime.now(UTC), status="draft",
                invoice_type="issued", amount_base=Decimal("10"),
                tax_amount=Decimal("2.1"), amount_total=Decimal("12.1"),
            )

        db.add(_issued("A2026-0001"))
        await db.flush()
        db.add(_issued("A2026-0001"))
        with pytest.raises(IntegrityError):
            await db.flush()
        await db.rollback()

    @pytest.mark.asyncio
    async def test_received_can_share_number_with_issued(self, db: AsyncSession):
        """Una recibida (nº del proveedor) puede coincidir con una emitida."""
        tenant, client = await _seed_tenant_client(db)
        uid = uuid4()
        lines = [{"description": "X", "quantity": 1, "unit_price": 10.0, "tax_percentage": 21.0}]
        await create_invoice(
            client.id,
            {"date": datetime.now(UTC), "status": "draft", "invoice_number": "A2026-0009"},
            lines, tenant.id, uid, db,
        )
        # Mismo string pero tipo 'received' → permitido (queda fuera del índice).
        recv = await create_invoice(
            client.id,
            {
                "date": datetime.now(UTC),
                "status": "draft",
                "invoice_number": "A2026-0009",
                "invoice_type": "received",
            },
            lines, tenant.id, uid, db,
        )
        assert recv.invoice_number == "A2026-0009"
        assert recv.invoice_type == "received"

    @pytest.mark.asyncio
    async def test_erp_create_produces_proforma(self, db: AsyncSession):
        """Toda emisión propia se degrada a PROFORMA sin número fiscal."""
        tenant, client = await _seed_tenant_client(db)
        invoice = await _create_basic_invoice(db, tenant, client)
        assert invoice.invoice_type == "proforma"
        assert invoice.invoice_number is None

    @pytest.mark.asyncio
    async def test_invoice_strips_frontend_totals(self, db: AsyncSession):
        """amount_base, tax_amount, amount_total in payload are ignored."""
        tenant, client = await _seed_tenant_client(db)
        uid = uuid4()
        payload = {
            "date": datetime.now(UTC),
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


class TestFacturaeProformaGuard:
    """Defensa en profundidad: generate_facturae_xml no debe producir una
    FacturaE oficial de una proforma, aunque se le llame directamente."""

    @pytest.mark.asyncio
    async def test_generate_facturae_raises_for_proforma(self, db: AsyncSession):
        from app.services.billing.facturae import ProformaNotFiscalError, generate_facturae_xml

        tenant, client = await _seed_tenant_client(db)
        invoice = await _create_basic_invoice(db, tenant, client)
        assert invoice.invoice_type == "proforma"
        assert invoice.invoice_number is None

        with pytest.raises(ProformaNotFiscalError):
            await generate_facturae_xml(invoice.id, tenant.id, db)

    def test_is_non_fiscal_proforma_predicate(self):
        from app.services.billing.facturae import is_non_fiscal_proforma

        # No fiscales → bloqueadas
        assert is_non_fiscal_proforma("proforma", None) is True
        assert is_non_fiscal_proforma("issued", None) is True
        assert is_non_fiscal_proforma("issued", "") is True
        assert is_non_fiscal_proforma("issued", "PROFORMA-abc12345") is True
        # Fiscales genuinas → permitidas
        assert is_non_fiscal_proforma("issued", "A2026-0001") is False
        assert is_non_fiscal_proforma("rectificativa", "R2026-0001") is False


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
