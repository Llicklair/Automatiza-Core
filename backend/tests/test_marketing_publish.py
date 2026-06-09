"""Tests de publicación: clasificación transitorio/permanente y reintentos.

`publish_post` se prueba con _dispatch mockeado (sin red). La política de
reintentos vive en `_handle_publish_result`, testeada sin DB.
"""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.db.models.marketing import ScheduledPost, SocialAccount
from app.services.encryption import encrypt_str
from app.services.marketing import publisher
from app.services.marketing.publisher import PublishResult
from app.workers import tasks_scheduler


async def _make_post(db, tenant_id, platform="twitter", token="tok"):
    account = SocialAccount(
        tenant_id=tenant_id,
        platform=platform,
        account_id="acc-1",
        access_token=encrypt_str(token) if token else "",
        token_expires_at=None,  # sin expiración → ensure_valid_token devuelve el token
    )
    db.add(account)
    await db.flush()
    post = ScheduledPost(
        tenant_id=tenant_id,
        social_account_id=account.id,
        platform=platform,
        content="hola mundo",
        status="scheduled",
    )
    db.add(post)
    await db.flush()
    return post


# ── publish_post: clasificación ──────────────────────────────────────────────

class TestPublishPostClassification:
    async def test_success(self, db, seed_tenant_and_user, monkeypatch):
        tenant, _, _ = seed_tenant_and_user
        post = await _make_post(db, tenant.id)

        async def _ok(*a, **k):
            return True, "PID123", None, 200

        monkeypatch.setattr(publisher, "_dispatch", _ok)
        result = await publisher.publish_post(post, db)
        assert result == PublishResult(True, False)
        assert post.status == "published"
        assert post.platform_post_id == "PID123"

    async def test_transient_5xx(self, db, seed_tenant_and_user, monkeypatch):
        tenant, _, _ = seed_tenant_and_user
        post = await _make_post(db, tenant.id)

        async def _fail(*a, **k):
            return False, None, "Twitter 503: down", 503

        monkeypatch.setattr(publisher, "_dispatch", _fail)
        result = await publisher.publish_post(post, db)
        assert result.ok is False and result.transient is True
        assert post.status == "failed"

    async def test_rate_limit_is_transient(self, db, seed_tenant_and_user, monkeypatch):
        tenant, _, _ = seed_tenant_and_user
        post = await _make_post(db, tenant.id)

        async def _fail(*a, **k):
            return False, None, "Twitter 429: rate", 429

        monkeypatch.setattr(publisher, "_dispatch", _fail)
        assert (await publisher.publish_post(post, db)).transient is True

    async def test_permanent_4xx(self, db, seed_tenant_and_user, monkeypatch):
        tenant, _, _ = seed_tenant_and_user
        post = await _make_post(db, tenant.id)

        async def _fail(*a, **k):
            return False, None, "Twitter 400: bad request", 400

        monkeypatch.setattr(publisher, "_dispatch", _fail)
        result = await publisher.publish_post(post, db)
        assert result.ok is False and result.transient is False

    async def test_exception_is_transient(self, db, seed_tenant_and_user, monkeypatch):
        tenant, _, _ = seed_tenant_and_user
        post = await _make_post(db, tenant.id)

        async def _boom(*a, **k):
            raise RuntimeError("conexión caída")

        monkeypatch.setattr(publisher, "_dispatch", _boom)
        result = await publisher.publish_post(post, db)
        assert result.ok is False and result.transient is True
        assert post.status == "failed"

    async def test_no_token_is_permanent(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        post = await _make_post(db, tenant.id, token="")  # cuenta sin token
        result = await publisher.publish_post(post, db)
        assert result == PublishResult(False, False)
        assert post.status == "failed"


# ── _handle_publish_result: política de reintentos ───────────────────────────

class TestHandlePublishResult:
    def _post(self, retry_count=0):
        return SimpleNamespace(
            retry_count=retry_count, status="scheduled",
            scheduled_at=None, error_message="boom",
        )

    def test_published(self):
        post = self._post()
        assert tasks_scheduler._handle_publish_result(post, PublishResult(True, False), datetime.now(UTC)) == "published"

    def test_transient_reschedules_with_backoff(self):
        now = datetime.now(UTC)
        post = self._post(retry_count=0)
        outcome = tasks_scheduler._handle_publish_result(post, PublishResult(False, True), now)
        assert outcome == "retried"
        assert post.retry_count == 1
        assert post.status == "scheduled"
        assert post.scheduled_at == now + timedelta(minutes=5)

    def test_backoff_doubles(self):
        now = datetime.now(UTC)
        post = self._post(retry_count=2)
        tasks_scheduler._handle_publish_result(post, PublishResult(False, True), now)
        # retry_count 2 → 3, delay = 5 * 2^(3-1) = 20 min
        assert post.retry_count == 3
        assert post.scheduled_at == now + timedelta(minutes=20)

    def test_retries_exhausted_fails(self):
        post = self._post(retry_count=tasks_scheduler._MAX_PUBLISH_RETRIES)
        outcome = tasks_scheduler._handle_publish_result(post, PublishResult(False, True), datetime.now(UTC))
        assert outcome == "failed"

    def test_permanent_fails_without_retry(self):
        post = self._post(retry_count=0)
        outcome = tasks_scheduler._handle_publish_result(post, PublishResult(False, False), datetime.now(UTC))
        assert outcome == "failed"
        assert post.retry_count == 0


# ── _publish_instagram: Instagram Graph API ──────────────────────────────────

class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


class _IGClient:
    """Contenedor → publicación, ambos vía graph.facebook.com."""

    def __init__(self):
        self.urls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, **kwargs):
        self.urls.append(url)
        if "media_publish" in url:
            return _FakeResponse(200, {"id": "MEDIA_ID"})
        if "/media" in url:
            return _FakeResponse(200, {"id": "CONTAINER_ID"})
        return _FakeResponse(404, {"error": "unmatched"})


class TestPublishInstagram:
    async def test_publishes_via_graph_facebook_with_ig_user_id(self, monkeypatch):
        client = _IGClient()
        monkeypatch.setattr(publisher.httpx, "AsyncClient", lambda *a, **k: client)
        ok, post_id, error, status = await publisher._publish_instagram(
            "PAGE_TOKEN", "una caption", "https://img/x.jpg", "IG_USER_9"
        )
        assert ok is True and post_id == "MEDIA_ID" and status == 200
        # Usa el Graph API de Facebook y el IG user id, no graph.instagram.com.
        assert all(u.startswith("https://graph.facebook.com") for u in client.urls)
        assert all("IG_USER_9" in u for u in client.urls)

    async def test_requires_image(self):
        ok, _, error, _ = await publisher._publish_instagram("t", "c", None, "IG1")
        assert ok is False and "imagen" in error.lower()

    async def test_requires_ig_user_id(self):
        ok, _, error, _ = await publisher._publish_instagram("t", "c", "https://img/x.jpg", None)
        assert ok is False and "id" in error.lower()
