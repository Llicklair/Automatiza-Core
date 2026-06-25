"""Publicación de posts vía Zernio (implementa `MarketingPublisher`).

Drop-in del antiguo `publisher.publish_post`: misma firma, NO lanza, actualiza el
`ScheduledPost` in-place. En el modelo BYO, `SocialAccount.account_id` guarda el
accountId de Zernio y la API key del usuario vive en `MarketingProviderConfig`.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.marketing import ScheduledPost, SocialAccount
from app.services.marketing.provider_config import client_for_account
from app.services.marketing.publisher_base import PublishResult
from app.services.marketing.zernio_client import ZernioClient, ZernioError

logger = logging.getLogger(__name__)


class ZernioPublisher:
    """Publica posts a través de la API de Zernio con la key del tenant."""

    async def publish_post(self, post: ScheduledPost, db: AsyncSession) -> PublishResult:
        res = await db.execute(
            select(SocialAccount).where(
                SocialAccount.id == post.social_account_id,
                SocialAccount.tenant_id == post.tenant_id,
            )
        )
        account = res.scalar_one_or_none()
        if account is None or not account.account_id:
            post.status = "failed"
            post.error_message = "Cuenta no conectada en Zernio (conéctala en Marketing → Cuentas)"
            return PublishResult(False, False)
        try:
            client = await client_for_account(db, account)
        except ZernioError as e:
            post.status = "failed"
            post.error_message = str(e)[:500]
            return PublishResult(False, False)
        return await self._do_publish(post, account, client)

    async def _do_publish(
        self, post: ScheduledPost, account: SocialAccount | None, client: ZernioClient
    ) -> PublishResult:
        """Publica con un cliente y cuenta ya resueltos (testeable sin BD)."""
        if account is None or not account.account_id:
            post.status = "failed"
            post.error_message = "Cuenta no conectada en Zernio (conéctala en Marketing → Cuentas)"
            return PublishResult(False, False)

        media = [post.image_url] if post.image_url else None
        try:
            zp = await client.create_post(
                content=post.content,
                platform=post.platform,
                account_id=account.account_id,
                media_urls=media,
                publish_now=True,
            )
        except ZernioError as e:
            post.status = "failed"
            post.error_message = str(e)[:500]
            return PublishResult(False, e.transient)

        post.status = "published"
        post.published_at = datetime.now(UTC)
        post.platform_post_id = zp.id or None
        post.error_message = None
        return PublishResult(True, False)
