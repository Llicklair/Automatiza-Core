"""Tests para app.services.sales.commands — flujo de stock en albaranes.

Foco: `update_albaran_status` debe descontar stock al pasar a `confirmed` y
revertirlo (movimiento entrada compensatorio) al volver a `draft`. Este flujo
es la deuda saldada el 2026-05-15 (ver tasks/lessons.md).
"""

from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.db.models.crm import Client
from app.db.models.inventory import Product, StockMovement
from app.services.sales.commands import (
    create_albaran,
    delete_albaran,
    update_albaran_status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _seed_client_and_product(
    db: AsyncSession, tenant_id, *, stock: int = 100
) -> tuple[Client, Product]:
    client = Client(
        id=uuid4(),
        tenant_id=tenant_id,
        nif="B12345678",
        name="Cliente Test",
    )
    product = Product(
        id=uuid4(),
        tenant_id=tenant_id,
        name="Producto X",
        sku="SKU-X",
        unit="ud",
        price=Decimal("10.00"),
        cost_price=Decimal("5.00"),
        stock_quantity=stock,
    )
    db.add_all([client, product])
    await db.flush()
    return client, product


def _line(product_id, qty: int, price: str = "10.00"):
    return SimpleNamespace(
        product_id=product_id,
        description="Línea test",
        quantity=qty,
        unit_price=Decimal(price),
        tax_percentage=Decimal("21.00"),
    )


# ── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestUpdateAlbaranStatus:
    async def test_pasar_a_confirmed_descuenta_stock(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        client, prod = await _seed_client_and_product(db, tenant.id, stock=50)
        note = await create_albaran(
            tenant_id=tenant.id,
            client_id=client.id,
            entry_date=None,
            notes=None,
            lines=[_line(prod.id, qty=10)],
            db=db,
        )

        result = await update_albaran_status(note.id, tenant.id, "confirmed", db)

        assert result.status == "confirmed"
        # Stock decremented
        prod_row = (
            await db.execute(select(Product).where(Product.id == prod.id))
        ).scalar_one()
        assert prod_row.stock_quantity == 40
        # StockMovement(salida) creado con reference correcta
        movs = (
            await db.execute(
                select(StockMovement).where(StockMovement.product_id == prod.id)
            )
        ).scalars().all()
        assert len(movs) == 1
        assert movs[0].movement_type == "salida"
        assert movs[0].quantity == 10
        assert movs[0].reference == f"DELIVERY_NOTE:{note.id}"

    async def test_confirmed_a_draft_revierte_stock(self, db, seed_tenant_and_user):
        """REGRESSION (deuda 2026-05-15): bajar confirmed→draft debe revertir stock."""
        tenant, _u, _t = seed_tenant_and_user
        client, prod = await _seed_client_and_product(db, tenant.id, stock=50)
        note = await create_albaran(
            tenant_id=tenant.id,
            client_id=client.id,
            entry_date=None,
            notes=None,
            lines=[_line(prod.id, qty=10)],
            db=db,
        )
        # Confirmar (stock pasa a 40)
        await update_albaran_status(note.id, tenant.id, "confirmed", db)

        # Volver a draft → debe revertir
        result = await update_albaran_status(note.id, tenant.id, "draft", db)

        assert result.status == "draft"
        prod_row = (
            await db.execute(select(Product).where(Product.id == prod.id))
        ).scalar_one()
        assert prod_row.stock_quantity == 50  # restaurado
        # Hay 2 movements: salida + entrada compensatoria
        movs = (
            await db.execute(
                select(StockMovement)
                .where(StockMovement.product_id == prod.id)
                .order_by(StockMovement.created_at)
            )
        ).scalars().all()
        assert len(movs) == 2
        types = {m.movement_type for m in movs}
        assert types == {"salida", "entrada"}
        entrada = next(m for m in movs if m.movement_type == "entrada")
        assert entrada.reference == f"DELIVERY_NOTE_REVERSED:{note.id}"

    async def test_idempotencia_doble_confirmacion_no_duplica_movements(
        self, db, seed_tenant_and_user
    ):
        tenant, _u, _t = seed_tenant_and_user
        client, prod = await _seed_client_and_product(db, tenant.id, stock=50)
        note = await create_albaran(
            tenant_id=tenant.id,
            client_id=client.id,
            entry_date=None,
            notes=None,
            lines=[_line(prod.id, qty=10)],
            db=db,
        )
        await update_albaran_status(note.id, tenant.id, "confirmed", db)
        # Re-aplicar mismo estado (debería no-op por la rama old==new)
        # Forzamos forzar el código del deduct yendo a delivered y volver
        # No probamos ese path — sólo el path que importa: confirmed → confirmed
        # no produce nuevos movimientos porque old_status == new_status.
        await update_albaran_status(note.id, tenant.id, "confirmed", db)

        movs = (
            await db.execute(
                select(StockMovement).where(StockMovement.product_id == prod.id)
            )
        ).scalars().all()
        assert len(movs) == 1  # sólo el primero

    async def test_falla_si_estado_invalido(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        client, prod = await _seed_client_and_product(db, tenant.id)
        note = await create_albaran(
            tenant_id=tenant.id,
            client_id=client.id,
            entry_date=None,
            notes=None,
            lines=[_line(prod.id, qty=1)],
            db=db,
        )
        with pytest.raises(ValueError, match="Estado"):
            await update_albaran_status(note.id, tenant.id, "shipped", db)

    async def test_falla_si_no_existe(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        with pytest.raises(LookupError):
            await update_albaran_status(uuid4(), tenant.id, "confirmed", db)

    async def test_confirmacion_falla_si_stock_insuficiente(
        self, db, seed_tenant_and_user
    ):
        tenant, _u, _t = seed_tenant_and_user
        client, prod = await _seed_client_and_product(db, tenant.id, stock=5)
        note = await create_albaran(
            tenant_id=tenant.id,
            client_id=client.id,
            entry_date=None,
            notes=None,
            lines=[_line(prod.id, qty=100)],  # más que el stock
            db=db,
        )
        with pytest.raises(ValueError, match="Stock insuficiente"):
            await update_albaran_status(note.id, tenant.id, "confirmed", db)

    async def test_delete_albaran_confirmado_revierte_stock(
        self, db, seed_tenant_and_user
    ):
        tenant, _u, _t = seed_tenant_and_user
        client, prod = await _seed_client_and_product(db, tenant.id, stock=30)
        note = await create_albaran(
            tenant_id=tenant.id,
            client_id=client.id,
            entry_date=None,
            notes=None,
            lines=[_line(prod.id, qty=7)],
            db=db,
        )
        await update_albaran_status(note.id, tenant.id, "confirmed", db)
        assert (
            await db.execute(select(Product.stock_quantity).where(Product.id == prod.id))
        ).scalar_one() == 23

        await delete_albaran(note.id, tenant.id, db)

        # Stock devuelto
        prod_row = (
            await db.execute(select(Product).where(Product.id == prod.id))
        ).scalar_one()
        assert prod_row.stock_quantity == 30
