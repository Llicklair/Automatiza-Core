"""E2E Marketing — una publicación que FALLA debe devolver error, no 200.

Bug (auditoría): `publish_post_now` descarta el `PublishResult` y devuelve HTTP
200 aunque la publicación falle (el post queda `status='failed'`, pero el front
lo da por publicado). Este test reproduce el fallo y blinda el contrato correcto.

Flujo Marketing de `tasks/iteraciones-cliente-real.md`.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.marketing import ScheduledPost, SocialAccount


@pytest.mark.asyncio
class TestMarketingPublishFalla:
    async def test_publish_sin_token_devuelve_error_no_200(
        self, auth_client: AsyncClient, db: AsyncSession, seed_tenant_and_user
    ):
        tenant, _user, _token = seed_tenant_and_user
        # Cuenta SIN token → publish_post devuelve PublishResult(ok=False)
        account = SocialAccount(
            tenant_id=tenant.id,
            platform="twitter",
            account_id="acc-1",
            account_name="@test",
            access_token="",  # vacío → falla "sin token"
        )
        db.add(account)
        await db.flush()
        post = ScheduledPost(
            tenant_id=tenant.id,
            social_account_id=account.id,
            platform="twitter",
            content="hola mundo",
            status="draft",
        )
        db.add(post)
        await db.commit()

        resp = await auth_client.post(f"/api/v1/marketing/posts/{post.id}/publish")

        # La publicación falla (cuenta sin token) → la API NO debe dar por publicado.
        assert resp.status_code >= 400, (
            f"publish_post_now devolvió {resp.status_code}: debe propagar el fallo, "
            f"no dar 200 a un post que quedó 'failed'. body={resp.text}"
        )
