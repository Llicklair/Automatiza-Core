"""Regresión R1 (2026-06-25): extracción de marketing.py → services.

- `social_accounts.disconnect_account`: desactiva la cuenta + llama a Zernio (404 se
  ignora, otros errores propagan).
- `publishing.publish_single_post` / `publish_posts_batch`: orquestan el publisher.

El cliente Zernio y el publisher se mockean.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.db.models.marketing import ScheduledPost, SocialAccount
from app.services.marketing import publishing
from app.services.marketing import social_accounts as social_accounts_svc
from app.services.marketing.publisher_base import PublishResult
from app.services.marketing.publishing import PostAlreadyPublishedError
from app.services.marketing.zernio_client import ZernioError


async def _seed_account(db, tenant_id) -> SocialAccount:
    acc = SocialAccount(tenant_id=tenant_id, platform="instagram", account_id="IG-1")
    db.add(acc)
    await db.commit()
    await db.refresh(acc)
    return acc


async def _seed_post(db, tenant_id, account_id, *, status="draft") -> ScheduledPost:
    post = ScheduledPost(
        tenant_id=tenant_id,
        social_account_id=account_id,
        platform="instagram",
        content="hola",
        status=status,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


def _fake_publisher(ok=True):
    pub = MagicMock()

    async def _publish(post, db):
        post.status = "published" if ok else "failed"
        if not ok:
            post.error_message = "fallo"
        return PublishResult(ok=ok, transient=False)

    pub.publish_post = _publish
    return pub


# ─── social_accounts.disconnect_account ───────────────────────────────────────


@pytest.mark.asyncio
async def test_disconnect_account_desactiva_y_llama_zernio(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    acc = await _seed_account(db, tenant.id)
    mock_client = MagicMock()
    mock_client.disconnect_account = AsyncMock()

    with patch(
        "app.services.marketing.social_accounts.client_for_account",
        new=AsyncMock(return_value=mock_client),
    ):
        ok = await social_accounts_svc.disconnect_account(acc.id, tenant.id, db)

    assert ok is True
    mock_client.disconnect_account.assert_awaited_once()
    await db.refresh(acc)  # recarga desde BD → confirma que se persistió
    assert acc.is_active is False


@pytest.mark.asyncio
async def test_disconnect_account_inexistente_devuelve_false(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    assert await social_accounts_svc.disconnect_account(uuid4(), tenant.id, db) is False


@pytest.mark.asyncio
async def test_disconnect_account_propaga_error_zernio_no_404(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    acc = await _seed_account(db, tenant.id)
    mock_client = MagicMock()
    mock_client.disconnect_account = AsyncMock(side_effect=ZernioError("boom", status=500))

    with patch(
        "app.services.marketing.social_accounts.client_for_account",
        new=AsyncMock(return_value=mock_client),
    ), pytest.raises(ZernioError):
        await social_accounts_svc.disconnect_account(acc.id, tenant.id, db)


# ─── publishing.publish_single_post / publish_posts_batch ─────────────────────


@pytest.mark.asyncio
async def test_publish_single_post_ok(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    acc = await _seed_account(db, tenant.id)
    post = await _seed_post(db, tenant.id, acc.id)

    with patch("app.services.marketing.publishing.get_publisher", return_value=_fake_publisher(ok=True)):
        res = await publishing.publish_single_post(post.id, tenant.id, db)

    assert res is not None
    published_post, ok = res
    assert ok is True
    assert published_post.status == "published"


@pytest.mark.asyncio
async def test_publish_single_post_inexistente(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    with patch("app.services.marketing.publishing.get_publisher", return_value=_fake_publisher()):
        assert await publishing.publish_single_post(uuid4(), tenant.id, db) is None


@pytest.mark.asyncio
async def test_publish_single_post_ya_publicado(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    acc = await _seed_account(db, tenant.id)
    post = await _seed_post(db, tenant.id, acc.id, status="published")

    with patch("app.services.marketing.publishing.get_publisher", return_value=_fake_publisher()), \
            pytest.raises(PostAlreadyPublishedError):
        await publishing.publish_single_post(post.id, tenant.id, db)


@pytest.mark.asyncio
async def test_publish_posts_batch_separa_ok_y_fallidos(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    acc = await _seed_account(db, tenant.id)
    p1 = await _seed_post(db, tenant.id, acc.id)
    missing = uuid4()

    with patch("app.services.marketing.publishing.get_publisher", return_value=_fake_publisher(ok=True)):
        result = await publishing.publish_posts_batch([p1.id, missing], tenant.id, db)

    assert str(p1.id) in result["published"]
    assert str(missing) in result["failed"]
