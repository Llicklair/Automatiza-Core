"""Contrato del decremento atómico de stock (anti-sobreventa).

`stock_service.decrement_product_stock` aplica un UPDATE condicional
`... WHERE stock_quantity >= qty`. Eso serializa peticiones concurrentes por
el row-lock del UPDATE: la segunda re-evalúa el WHERE sobre el valor ya
decrementado, así que el stock NUNCA queda negativo (anti-sobreventa).

NOTA sobre concurrencia real: la infra de test usa SQLite en memoria con
StaticPool (una sola conexión compartida — ver conftest.py), por lo que NO se
pueden abrir dos conexiones concurrentes reales contra la misma BD para
reproducir la carrera. La corrección se sostiene por el UPDATE atómico; aquí
verificamos el CONTRATO del helper en una sesión. La reproducción de la carrera
requeriría Postgres (o SQLite en fichero con conexiones separadas).
"""
import pytest

from app.db.models.inventory import Product
from app.services.inventory import stock_service


async def _add_product(db, tenant_id, stock_quantity):
    p = Product(
        tenant_id=tenant_id,
        name="Producto",
        sku="P-1",
        stock_quantity=stock_quantity,
        price=10,
        cost_price=5,
        is_active=True,
    )
    db.add(p)
    await db.flush()
    return p


@pytest.mark.asyncio
async def test_decrement_exact_to_zero(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    p = await _add_product(db, tenant.id, stock_quantity=5)

    await stock_service.decrement_product_stock(db, p, 5)

    assert int(p.stock_quantity) == 0


@pytest.mark.asyncio
async def test_decrement_partial(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    p = await _add_product(db, tenant.id, stock_quantity=5)

    await stock_service.decrement_product_stock(db, p, 2)

    assert int(p.stock_quantity) == 3


@pytest.mark.asyncio
async def test_overdraw_raises_and_keeps_stock(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    p = await _add_product(db, tenant.id, stock_quantity=5)

    with pytest.raises(ValueError, match="Stock insuficiente"):
        await stock_service.decrement_product_stock(db, p, 6)

    # El UPDATE condicional no tocó nada: el stock sigue intacto (no negativo).
    assert int(p.stock_quantity) == 5


@pytest.mark.asyncio
async def test_zero_or_negative_qty_is_noop(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    p = await _add_product(db, tenant.id, stock_quantity=5)

    await stock_service.decrement_product_stock(db, p, 0)
    await stock_service.decrement_product_stock(db, p, -3)

    assert int(p.stock_quantity) == 5


@pytest.mark.asyncio
async def test_sequential_overdraw_never_negative(db, seed_tenant_and_user):
    """Dos decrementos de 5 sobre stock=5: el primero deja 0, el segundo falla.

    Aproxima el invariante de la carrera (exactamente uno pasa, el stock final es
    0, nunca negativo) de forma secuencial — lo único reproducible con la infra
    de test actual (StaticPool, sin conexiones concurrentes).
    """
    tenant, _u, _t = seed_tenant_and_user
    p = await _add_product(db, tenant.id, stock_quantity=5)

    await stock_service.decrement_product_stock(db, p, 5)
    assert int(p.stock_quantity) == 0

    with pytest.raises(ValueError, match="Stock insuficiente"):
        await stock_service.decrement_product_stock(db, p, 5)

    assert int(p.stock_quantity) == 0
