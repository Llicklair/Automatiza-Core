"""E2E Marketing — happy path: crear post → publicar OK → queda 'published'.

Complementa `test_e2e_marketing_publish.py` (que cubre la RUTA DE ERROR: publicar sin token
→ 502). Aquí se cubre el camino feliz: con una cuenta conectada y el publisher resolviendo
correctamente, POST .../publish marca el post como 'published' y guarda el platform_post_id.

El publisher real habla con Zernio (externo); se sustituye `get_publisher()` por un fake
determinista (mismo contrato que ZernioPublisher) para no depender de la red.
"""
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.marketing import SocialAccount
from app.services.marketing.publisher_base import PublishResult


class _FakePublisher:
    """Publisher determinista: marca el post como publicado sin llamar a Zernio."""

    async def publish_post(self, post, db):
        post.status = "published"
        post.published_at = datetime.now(UTC)
        post.platform_post_id = "zernio-fake-123"
        post.error_message = None
        return PublishResult(True, False)


@pytest.mark.asyncio
class TestMarketingPublishHappyPath:
    async def test_crear_y_publicar_ok(
        self, auth_client: AsyncClient, db: AsyncSession, seed_tenant_and_user, monkeypatch
    ):
        tenant, _user, _token = seed_tenant_and_user
        # Cuenta conectada (account_id de Zernio presente).
        account = SocialAccount(
            tenant_id=tenant.id,
            platform="twitter",
            account_id="zernio-acc-1",
            account_name="@test",
        )
        db.add(account)
        await db.commit()
        await db.refresh(account)

        # El publisher real habla con Zernio: lo sustituimos por uno determinista.
        # (get_publisher se importa dentro del handler desde este módulo origen.)
        monkeypatch.setattr(
            "app.services.marketing.publishing.get_publisher", lambda: _FakePublisher()
        )

        # 1) Crear el post (queda en draft).
        create = await auth_client.post("/api/v1/marketing/posts", json={
            "social_account_id": str(account.id),
            "platform": "twitter",
            "content": "Lanzamiento de producto 🚀",
        })
        assert create.status_code == 201, create.text
        post_id = create.json()["id"]
        assert create.json()["status"] == "draft"

        # 2) Publicar ahora → 200 y queda 'published' con su id de plataforma.
        pub = await auth_client.post(f"/api/v1/marketing/posts/{post_id}/publish")
        assert pub.status_code == 200, pub.text
        body = pub.json()
        assert body["status"] == "published"
        assert body["platform_post_id"] == "zernio-fake-123"

        # 3) Aparece en el listado de publicados.
        published = await auth_client.get(
            "/api/v1/marketing/posts", params={"status": "published"}
        )
        assert published.status_code == 200
        assert post_id in [p["id"] for p in published.json()]
