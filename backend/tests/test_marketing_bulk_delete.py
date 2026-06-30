"""Borrado en masa de posts de marketing (pestaña Programados → 'Eliminar todos').

Invariante de seguridad: un post 'published' NUNCA se borra.
"""

import pytest
from sqlalchemy import select

from app.db.models.marketing import ScheduledPost, SocialAccount
from app.services.marketing.posts import delete_posts_bulk

pytestmark = pytest.mark.asyncio


async def _account(db, tenant_id) -> SocialAccount:
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


def _post(tenant_id, acc_id, status) -> ScheduledPost:
    return ScheduledPost(
        tenant_id=tenant_id,
        social_account_id=acc_id,
        platform="instagram",
        content=f"post {status}",
        status=status,
    )


async def _remaining(db, tenant_id):
    res = await db.execute(select(ScheduledPost).where(ScheduledPost.tenant_id == tenant_id))
    return res.scalars().all()


async def test_borra_no_publicados_y_respeta_publicados(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    acc = await _account(db, tenant.id)
    db.add(_post(tenant.id, acc.id, "draft"))
    db.add(_post(tenant.id, acc.id, "scheduled"))
    db.add(_post(tenant.id, acc.id, "scheduled"))
    db.add(_post(tenant.id, acc.id, "published"))
    await db.commit()

    deleted = await delete_posts_bulk(tenant.id, db)

    assert deleted == 3
    remaining = await _remaining(db, tenant.id)
    assert len(remaining) == 1
    assert remaining[0].status == "published"


async def test_filtra_por_status(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    acc = await _account(db, tenant.id)
    db.add(_post(tenant.id, acc.id, "draft"))
    db.add(_post(tenant.id, acc.id, "scheduled"))
    db.add(_post(tenant.id, acc.id, "scheduled"))
    await db.commit()

    deleted = await delete_posts_bulk(tenant.id, db, status_filter="scheduled")

    assert deleted == 2
    remaining = await _remaining(db, tenant.id)
    assert len(remaining) == 1
    assert remaining[0].status == "draft"


async def test_filtra_por_ids(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    acc = await _account(db, tenant.id)
    p1 = _post(tenant.id, acc.id, "draft")
    p2 = _post(tenant.id, acc.id, "scheduled")
    db.add(p1)
    db.add(p2)
    await db.commit()
    await db.refresh(p1)
    await db.refresh(p2)

    deleted = await delete_posts_bulk(tenant.id, db, ids=[p1.id])

    assert deleted == 1
    remaining = await _remaining(db, tenant.id)
    assert {p.id for p in remaining} == {p2.id}
