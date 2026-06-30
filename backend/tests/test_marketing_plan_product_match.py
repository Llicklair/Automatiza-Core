"""Repro: 'Generar plan' debe respetar el producto que pide el usuario.

Bug observado (capturas del panel Marketing → Plan IA): al pedir una campaña
para un producto concreto del catálogo, el agente caía al fallback determinista
y este IGNORABA el texto, cogiendo los 3 productos más NUEVOS del catálogo.
Resultado: pediste "Switch Pro" y te plantó Ladrillo Pro / Batería Mini / Cristal.
"""

import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.db.models.inventory import Product
from app.db.models.marketing import ScheduledPost, SocialAccount
from app.services.marketing.plan_generation import generate_plan

pytestmark = pytest.mark.asyncio

_BASE = datetime.datetime(2026, 6, 1, tzinfo=datetime.timezone.utc)


async def _seed_account(db, tenant_id) -> SocialAccount:
    acc = SocialAccount(
        tenant_id=tenant_id,
        platform="instagram",
        account_id="ig1",
        account_name="@pyme",
        is_active=True,
    )
    db.add(acc)
    await db.flush()
    return acc


def _product(tenant_id, name, *, days_old, desc=None):
    return Product(
        tenant_id=tenant_id,
        name=name,
        description=desc,
        price=Decimal("556.00"),
        created_at=_BASE - datetime.timedelta(days=days_old),
    )


async def test_fallback_respeta_el_producto_pedido(db, seed_tenant_and_user):
    """Pido 'Switch Pro' (en catálogo, NO el más nuevo) → los posts hablan de Switch Pro."""
    tenant, _u, _t = seed_tenant_and_user
    # Switch Pro es ANTIGUO; los decoys son los 3 más nuevos del catálogo.
    db.add(_product(tenant.id, "Switch Pro", days_old=30, desc="La consola portátil definitiva."))
    db.add(_product(tenant.id, "Ladrillo Pro", days_old=2))
    db.add(_product(tenant.id, "Bateria Mini", days_old=1))
    db.add(_product(tenant.id, "Cristal Mini", days_old=0))
    await _seed_account(db, tenant.id)
    await db.commit()

    # El agente LLM no crea nada (simula create_campaign gateada bajo CONFIRM) → cae al fallback.
    with patch("app.agents.marketing.run_agent", new=AsyncMock(return_value=[])), \
         patch("app.services.marketing.image_search.search_image", new=AsyncMock(return_value=None)):
        summary, post_ids = await generate_plan(
            db, tenant.id, "generame una campaña de marketing para la switch pro"
        )

    posts = (
        await db.execute(select(ScheduledPost).where(ScheduledPost.tenant_id == tenant.id))
    ).scalars().all()
    assert posts, "el fallback debe crear al menos un borrador"
    blob = " ".join(p.content for p in posts)
    assert "Switch Pro" in blob, f"esperaba Switch Pro, obtuve: {blob!r}"
    assert "Ladrillo" not in blob and "Cristal" not in blob, (
        f"no debe meter productos que no pediste: {blob!r}"
    )


async def test_sin_producto_nombrado_usa_destacados(db, seed_tenant_and_user):
    """Sin producto concreto en el texto → comportamiento clásico: usa el catálogo (no rompe)."""
    tenant, _u, _t = seed_tenant_and_user
    db.add(_product(tenant.id, "Camiseta Verano", days_old=2))
    db.add(_product(tenant.id, "Gorra Playa", days_old=1))
    await _seed_account(db, tenant.id)
    await db.commit()

    with patch("app.agents.marketing.run_agent", new=AsyncMock(return_value=[])), \
         patch("app.services.marketing.image_search.search_image", new=AsyncMock(return_value=None)):
        summary, post_ids = await generate_plan(
            db, tenant.id, "un plan de contenidos para este mes"
        )

    posts = (
        await db.execute(select(ScheduledPost).where(ScheduledPost.tenant_id == tenant.id))
    ).scalars().all()
    assert posts, "debe generar borradores desde el catálogo cuando no se nombra producto"
