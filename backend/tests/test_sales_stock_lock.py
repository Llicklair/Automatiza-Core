"""
Tests empíricos para el RMW race en _deduct_stock_for_albaran.

Usa Postgres REAL en localhost:5433. Cada test crea su propio engine
por test (evita "Future attached to a different loop" de asyncpg con
pytest-asyncio que asigna un loop nuevo por test).

El tenant_id actúa como namespace de aislamiento; RLS se maneja mediante:
  - rls_bypass() para insertar el Tenant (no hay tenant en contexto aún)
  - set_current_tenant(str(tenant.id)) para el resto de operaciones

Hipótesis de bug: sin SELECT ... FOR UPDATE en _deduct_stock_for_albaran,
dos confirmaciones concurrentes leen el mismo stock_quantity y una deducción
se pierde (lost update / ghost stock / overselling).

Para ejecutar sólo estos tests:
    pytest tests/test_sales_stock_lock.py -q
"""

import asyncio
import os
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ── Env vars necesarias ANTES de importar la app ─────────────────────────────
os.environ.setdefault("SECRET_KEY", "test_secret_key_stock_lock_1234567890abcdef")
os.environ.setdefault("TENANT_ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

PG_URL = "postgresql+asyncpg://pyme_app:pyme_pass@localhost:5433/pyme_db"

# ── Importar modelos y RLS DESPUÉS de fijar las env vars ─────────────────────
from app.core.tenant_context import rls_bypass, set_current_tenant
from app.db.models.crm import Client
from app.db.models.inventory import Product, StockMovement
from app.db.models.billing import DeliveryNote
from app.db.models.models import Tenant
from app.db.rls import install_rls_listener
from app.services.sales.commands import create_albaran, update_albaran_status


# ── Factory: engine + sessionmaker frescos por test ──────────────────────────

def _make_engine_and_session():
    """Crea engine y sessionmaker nuevos ligados al loop actual del test."""
    engine = create_async_engine(PG_URL, echo=False, pool_pre_ping=False)
    install_rls_listener(engine)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, Session


# ── Seed helpers ─────────────────────────────────────────────────────────────

async def _make_tenant(db: AsyncSession) -> Tenant:
    """Inserta un Tenant con bypass RLS (no hay tenant en contexto todavía)."""
    tenant = Tenant(
        id=uuid4(),
        name=f"Empresa-{uuid4().hex[:6]}",
        nif=f"B{uuid4().int % 10**8:08d}",
        plan="starter",
    )
    with rls_bypass():
        db.add(tenant)
        await db.flush()
    return tenant


async def _make_product(db: AsyncSession, tenant_id, *, stock: int) -> Product:
    product = Product(
        id=uuid4(),
        tenant_id=tenant_id,
        name=f"Prod-{uuid4().hex[:6]}",
        sku=f"SKU-{uuid4().hex[:8]}",
        unit="ud",
        price=Decimal("10.00"),
        cost_price=Decimal("5.00"),
        stock_quantity=stock,
    )
    db.add(product)
    await db.flush()
    return product


async def _make_client(db: AsyncSession, tenant_id) -> Client:
    client = Client(
        id=uuid4(),
        tenant_id=tenant_id,
        nif=f"B{uuid4().int % 10**8:08d}",
        name=f"Cliente-{uuid4().hex[:6]}",
    )
    db.add(client)
    await db.flush()
    return client


def _line_ns(product_id, qty: int):
    return SimpleNamespace(
        product_id=product_id,
        description="Línea test",
        quantity=qty,
        unit_price=Decimal("10.00"),
        tax_percentage=Decimal("21.00"),
    )


async def _cleanup(Session, tenant_id: str) -> None:
    """Borra todos los datos del tenant de prueba en orden FK-safe.
    delivery_note_lines no tiene tenant_id — se borran en cascada al borrar
    delivery_notes (ondelete=CASCADE), o explícitamente por albaran_id.
    """
    with rls_bypass():
        async with Session() as db:
            await db.execute(
                text("DELETE FROM stock_movements WHERE tenant_id = :t"), {"t": tenant_id}
            )
            # Lines cascade from notes (ondelete=CASCADE), delete notes first
            await db.execute(
                text("DELETE FROM delivery_notes WHERE tenant_id = :t"), {"t": tenant_id}
            )
            await db.execute(
                text("DELETE FROM products WHERE tenant_id = :t"), {"t": tenant_id}
            )
            await db.execute(
                text("DELETE FROM clients WHERE tenant_id = :t"), {"t": tenant_id}
            )
            await db.execute(
                text("DELETE FROM tenants WHERE id = :t"), {"t": tenant_id}
            )
            await db.commit()


# ── Test 1: Conservation (sequential) ────────────────────────────────────────

@pytest.mark.asyncio
async def test_conservation_sequential():
    """Confirmar un albarán descuenta stock exactamente; aritmética correcta."""
    engine, Session = _make_engine_and_session()
    tenant_id_str = None
    try:
        async with Session() as db:
            tenant = await _make_tenant(db)
            tenant_id_str = str(tenant.id)
            set_current_tenant(tenant_id_str)
            client = await _make_client(db, tenant.id)
            product = await _make_product(db, tenant.id, stock=50)
            note = await create_albaran(
                tenant_id=tenant.id, client_id=client.id,
                entry_date=None, notes=None,
                lines=[_line_ns(product.id, qty=15)], db=db,
            )
            await db.commit()

        set_current_tenant(tenant_id_str)
        async with Session() as db:
            await update_albaran_status(note.id, tenant.id, "confirmed", db)

        async with Session() as db:
            row = (
                await db.execute(select(Product).where(Product.id == product.id))
            ).scalar_one()
            assert row.stock_quantity == 35, (
                f"Esperado 35, obtenido {row.stock_quantity}"
            )
    finally:
        set_current_tenant(None)
        if tenant_id_str:
            await _cleanup(Session, tenant_id_str)
        await engine.dispose()


# ── Test 2: Conservation after confirm + revert ───────────────────────────────

@pytest.mark.asyncio
async def test_conservation_confirm_then_revert():
    """Confirmar luego revertir devuelve el stock al valor original exacto."""
    engine, Session = _make_engine_and_session()
    tenant_id_str = None
    try:
        async with Session() as db:
            tenant = await _make_tenant(db)
            tenant_id_str = str(tenant.id)
            set_current_tenant(tenant_id_str)
            client = await _make_client(db, tenant.id)
            product = await _make_product(db, tenant.id, stock=30)
            note = await create_albaran(
                tenant_id=tenant.id, client_id=client.id,
                entry_date=None, notes=None,
                lines=[_line_ns(product.id, qty=10)], db=db,
            )
            await db.commit()

        set_current_tenant(tenant_id_str)
        async with Session() as db:
            await update_albaran_status(note.id, tenant.id, "confirmed", db)

        async with Session() as db:
            row = (
                await db.execute(select(Product).where(Product.id == product.id))
            ).scalar_one()
            assert row.stock_quantity == 20, (
                f"Tras confirmar esperado 20, obtenido {row.stock_quantity}"
            )

        async with Session() as db:
            await update_albaran_status(note.id, tenant.id, "draft", db)

        async with Session() as db:
            row = (
                await db.execute(select(Product).where(Product.id == product.id))
            ).scalar_one()
            assert row.stock_quantity == 30, (
                f"Tras revertir esperado 30, obtenido {row.stock_quantity}"
            )
    finally:
        set_current_tenant(None)
        if tenant_id_str:
            await _cleanup(Session, tenant_id_str)
        await engine.dispose()


# ── Test 3: Oversell rejection ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_oversell_rejected_stock_unchanged():
    """Deducir más que el stock disponible lanza ValueError; stock queda intacto."""
    engine, Session = _make_engine_and_session()
    tenant_id_str = None
    try:
        async with Session() as db:
            tenant = await _make_tenant(db)
            tenant_id_str = str(tenant.id)
            set_current_tenant(tenant_id_str)
            client = await _make_client(db, tenant.id)
            product = await _make_product(db, tenant.id, stock=5)
            note = await create_albaran(
                tenant_id=tenant.id, client_id=client.id,
                entry_date=None, notes=None,
                lines=[_line_ns(product.id, qty=10)], db=db,
            )
            await db.commit()

        set_current_tenant(tenant_id_str)
        with pytest.raises(ValueError, match="[Ss]tock insuficiente"):
            async with Session() as db:
                await update_albaran_status(note.id, tenant.id, "confirmed", db)

        async with Session() as db:
            row = (
                await db.execute(select(Product).where(Product.id == product.id))
            ).scalar_one()
            assert row.stock_quantity == 5, (
                f"Stock no debe cambiar tras oversell; obtenido {row.stock_quantity}"
            )
    finally:
        set_current_tenant(None)
        if tenant_id_str:
            await _cleanup(Session, tenant_id_str)
        await engine.dispose()


# ── Test 4: Concurrency — lost-update repro ───────────────────────────────────

@pytest.mark.asyncio
async def test_concurrent_deductions_lost_update():
    """
    REPRO del bug RMW sin bloqueo de fila.

    Escenario: stock=10, dos albaranes de qty=5 cada uno se confirman
    concurrentemente con asyncio.gather. Sin FOR UPDATE, ambas sesiones leen
    stock=10 antes de que cualquiera commitee, calculan new_stock=5, y la
    segunda escritura sobreescribe a la primera — resultado final: stock=5
    en lugar de 0 (deducción perdida / ghost stock / overselling).

    Con el fix correcto (FOR UPDATE) las sesiones se serializan:
      - O bien la segunda espera a que la primera commitee y entonces lee
        stock=5, calcula new_stock=0 y commitea correctamente → stock=0.
      - O bien la segunda ve stock=5 < qty=5 y lanza ValueError → correcto.

    Lógica de veredicto:
      - Si en ≥1 de 5 iteraciones el stock final es 5 (ambas commitaron pero
        una se perdió) → BUG CONFIRMADO, test FALLA.
      - Si en todos los intentos el resultado es 0 o una sesión lanza
        ValueError → el código serializa correctamente → test PASA.

    PRE-FIX (sin FOR UPDATE): test FALLA con "BUG CONFIRMADO".
    POST-FIX (con FOR UPDATE): test PASA.
    """
    engine, Session = _make_engine_and_session()
    tenant_id_str = None
    lost_update_detected = False

    try:
        async with Session() as db:
            tenant = await _make_tenant(db)
            tenant_id_str = str(tenant.id)
            set_current_tenant(tenant_id_str)
            client = await _make_client(db, tenant.id)
            product = await _make_product(db, tenant.id, stock=10)
            await db.commit()

        tenant_id = tenant.id
        client_id = client.id
        product_id = product.id

        for _attempt in range(5):
            # Reset stock to 10 for this iteration
            set_current_tenant(tenant_id_str)
            async with Session() as db:
                prod_row = (
                    await db.execute(select(Product).where(Product.id == product_id))
                ).scalar_one()
                prod_row.stock_quantity = 10
                await db.commit()

            # Create two fresh albaranes (no stock touch yet)
            async with Session() as db:
                n1 = await create_albaran(
                    tenant_id=tenant_id, client_id=client_id,
                    entry_date=None, notes=None,
                    lines=[_line_ns(product_id, qty=5)], db=db,
                )
                await db.commit()

            async with Session() as db:
                n2 = await create_albaran(
                    tenant_id=tenant_id, client_id=client_id,
                    entry_date=None, notes=None,
                    lines=[_line_ns(product_id, qty=5)], db=db,
                )
                await db.commit()

            # Concurrent confirmations. asyncio.gather starts both coroutines
            # before either commits. Without FOR UPDATE, both read stock=10,
            # compute new_stock=5, and both commit — second overwrites first
            # (lost update → stock=5 instead of 0).
            both_succeeded = True

            async def confirm(note_id):
                set_current_tenant(tenant_id_str)
                async with Session() as db:
                    await update_albaran_status(note_id, tenant_id, "confirmed", db)

            try:
                await asyncio.gather(confirm(n1.id), confirm(n2.id))
            except ValueError:
                # One session saw the other's committed stock and raised
                # "Stock insuficiente" — this is CORRECT serialized behaviour.
                both_succeeded = False

            if both_succeeded:
                set_current_tenant(tenant_id_str)
                async with Session() as db:
                    final = (
                        await db.execute(
                            select(Product.stock_quantity).where(
                                Product.id == product_id
                            )
                        )
                    ).scalar_one()

                if final == 5:
                    lost_update_detected = True
                elif final != 0:
                    pytest.fail(
                        f"Valor de stock inesperado: {final} "
                        f"(esperado 0 con FOR UPDATE, 5 sin él)."
                    )

            # Clean up iteration data (movements + notes cascade-delete lines)
            set_current_tenant(tenant_id_str)
            async with Session() as db:
                await db.execute(
                    text("DELETE FROM stock_movements WHERE tenant_id = :t"),
                    {"t": tenant_id_str},
                )
                await db.execute(
                    text("DELETE FROM delivery_notes WHERE tenant_id = :t"),
                    {"t": tenant_id_str},
                )
                await db.commit()

            if lost_update_detected:
                break

    finally:
        set_current_tenant(None)
        if tenant_id_str:
            await _cleanup(Session, tenant_id_str)
        await engine.dispose()

    # ── Veredicto ─────────────────────────────────────────────────────────────
    # PRE-FIX: lost_update_detected=True → assert FALLA → BUG CONFIRMADO.
    # POST-FIX: lost_update_detected=False → assert PASA → bug corregido.
    assert not lost_update_detected, (
        "BUG CONFIRMADO (lost-update / ghost stock): "
        "dos confirmaciones concurrentes del mismo albarán leyeron stock=10, "
        "ambas calcularon new_stock=5 y ambas commitearon — la segunda "
        "sobrescribió a la primera. Stock final=5 en lugar de 0. "
        "5 unidades fantasma disponibles para venta sin stock real. "
        "FIX: añadir .with_for_update() al SELECT de Product en "
        "_deduct_stock_for_albaran (app/services/sales/commands.py ~línea 527)."
    )
