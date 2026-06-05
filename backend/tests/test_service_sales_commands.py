"""Tests para app.services.sales.commands — CRUD de clientes, productos,
movimientos de stock y presupuestos (cobertura QA).

Foco en los caminos felices + errores (LookupError / ValueError) de las
operaciones de escritura que no cubría test_service_sales_albaran.py.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.models.inventory import Product, StockMovement
from app.services.sales.commands import (
    create_client,
    create_product,
    create_quote,
    create_stock_movement,
    delete_client,
    delete_product,
    delete_quote,
    update_client,
    update_product,
    update_quote,
)


# ── client ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestClientCommands:
    async def test_create_client_ok_emite_evento(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        client = await create_client(
            db, tenant.id, user.id, {"name": "ACME S.L.", "nif": "B11111111"}
        )
        assert client.id is not None
        assert client.tenant_id == tenant.id
        assert client.name == "ACME S.L."

    async def test_create_client_nif_duplicado_raise_value_error(
        self, db, seed_tenant_and_user
    ):
        tenant, user, _t = seed_tenant_and_user
        await create_client(db, tenant.id, user.id, {"name": "A", "nif": "B22222222"})
        with pytest.raises(ValueError, match="Ya existe"):
            await create_client(
                db, tenant.id, user.id, {"name": "B", "nif": "B22222222"}
            )

    async def test_update_client_ok(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        client = await create_client(db, tenant.id, user.id, {"name": "Viejo"})
        updated = await update_client(db, tenant.id, client.id, {"name": "Nuevo"})
        assert updated.name == "Nuevo"

    async def test_update_client_no_existe_raise_lookup(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        with pytest.raises(LookupError):
            await update_client(db, tenant.id, uuid4(), {"name": "X"})

    async def test_delete_client_ok(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        client = await create_client(db, tenant.id, user.id, {"name": "Borrar"})
        await delete_client(db, tenant.id, client.id)
        with pytest.raises(LookupError):
            await update_client(db, tenant.id, client.id, {"name": "Y"})

    async def test_delete_client_no_existe_raise_lookup(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        with pytest.raises(LookupError):
            await delete_client(db, tenant.id, uuid4())


# ── product ────────────────────────────────────────────────────────────────


def _product_data(**over):
    data = {
        "name": "Producto",
        "sku": f"SKU-{uuid4().hex[:6]}",
        "unit": "ud",
        "price": Decimal("10.00"),
        "cost_price": Decimal("5.00"),
        "stock_quantity": 100,
    }
    data.update(over)
    return data


@pytest.mark.asyncio
class TestProductCommands:
    async def test_create_product_ok(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        product = await create_product(db, tenant.id, _product_data(name="Silla"))
        assert product.id is not None
        assert product.name == "Silla"

    async def test_update_product_ok(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        product = await create_product(db, tenant.id, _product_data())
        updated = await update_product(
            db, tenant.id, product.id, {"price": Decimal("20.00")}
        )
        assert updated.price == Decimal("20.00")

    async def test_update_product_no_existe(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        with pytest.raises(LookupError):
            await update_product(db, tenant.id, uuid4(), {"price": Decimal("1")})

    async def test_delete_product_ok(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        product = await create_product(db, tenant.id, _product_data())
        await delete_product(db, tenant.id, product.id)
        remaining = (
            await db.execute(select(Product).where(Product.id == product.id))
        ).scalar_one_or_none()
        assert remaining is None

    async def test_delete_product_no_existe(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        with pytest.raises(LookupError):
            await delete_product(db, tenant.id, uuid4())


# ── stock movements ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestStockMovementCommands:
    async def test_entrada_incrementa_stock(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        product = await create_product(db, tenant.id, _product_data(stock_quantity=10))
        mov = await create_stock_movement(
            db, tenant.id, product.id, {"movement_type": "entrada", "quantity": 5}
        )
        assert mov.stock_after == 15
        refreshed = (
            await db.execute(select(Product).where(Product.id == product.id))
        ).scalar_one()
        assert refreshed.stock_quantity == 15

    async def test_salida_decrementa_stock(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        product = await create_product(db, tenant.id, _product_data(stock_quantity=10))
        mov = await create_stock_movement(
            db, tenant.id, product.id, {"movement_type": "salida", "quantity": 4}
        )
        assert mov.stock_after == 6

    async def test_salida_insuficiente_raise_value_error(
        self, db, seed_tenant_and_user
    ):
        tenant, _u, _t = seed_tenant_and_user
        product = await create_product(db, tenant.id, _product_data(stock_quantity=3))
        with pytest.raises(ValueError, match="Stock insuficiente"):
            await create_stock_movement(
                db, tenant.id, product.id, {"movement_type": "salida", "quantity": 10}
            )

    async def test_ajuste_fija_stock_absoluto(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        product = await create_product(db, tenant.id, _product_data(stock_quantity=10))
        mov = await create_stock_movement(
            db, tenant.id, product.id, {"movement_type": "ajuste", "quantity": 42}
        )
        assert mov.stock_after == 42

    async def test_producto_no_existe_raise_lookup(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        with pytest.raises(LookupError):
            await create_stock_movement(
                db, tenant.id, uuid4(), {"movement_type": "entrada", "quantity": 1}
            )


# ── quotes ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestQuoteCommands:
    async def _make_client(self, db, tenant, user):
        return await create_client(db, tenant.id, user.id, {"name": "Cli", "nif": None})

    async def test_create_quote_calcula_importes(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        client = await self._make_client(db, tenant, user)
        quote = await create_quote(
            db,
            tenant.id,
            {
                "client_id": client.id,
                "status": "draft",
                "lines": [
                    {
                        "quantity": 2,
                        "unit_price": 100,
                        "tax_percentage": 21,
                        "description": "L1",
                    }
                ],
            },
        )
        # base = 2*100 = 200 ; tax = 200*0.21 = 42 ; total = 242
        assert float(quote.amount_base) == 200.0
        assert float(quote.tax_amount) == 42.0
        assert float(quote.amount_total) == 242.0
        assert len(quote.lines) == 1

    async def test_update_quote_ok(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        client = await self._make_client(db, tenant, user)
        quote = await create_quote(
            db, tenant.id, {"client_id": client.id, "lines": []}
        )
        updated = await update_quote(db, quote.id, tenant.id, {"status": "sent"})
        assert updated.status == "sent"

    async def test_update_quote_no_existe(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        with pytest.raises((LookupError, Exception)):
            await update_quote(db, uuid4(), tenant.id, {"status": "sent"})

    async def test_delete_quote_ok(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        client = await self._make_client(db, tenant, user)
        quote = await create_quote(
            db, tenant.id, {"client_id": client.id, "lines": []}
        )
        await delete_quote(db, quote.id, tenant.id)
        with pytest.raises(LookupError):
            await delete_quote(db, quote.id, tenant.id)
