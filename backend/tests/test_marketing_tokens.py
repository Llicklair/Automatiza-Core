"""Tests del ciclo de vida de tokens OAuth de marketing.

Cubre el cifrado de strings (encrypt_str/decrypt_str con compat legacy) y la
renovación de tokens (ensure_valid_token) con httpx mockeado — sin red real.
"""
from datetime import UTC, datetime, timedelta

from app.db.models.marketing import SocialAccount
from app.services.encryption import decrypt_str, encrypt_str
from app.services.marketing import oauth_tokens


# ── Helpers de mock ──────────────────────────────────────────────────────────

class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self) -> dict:
        return self._payload


class _FakeClient:
    """Sustituye httpx.AsyncClient: devuelve siempre la misma respuesta."""

    def __init__(self, status_code: int, payload: dict):
        self._status = status_code
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, **kwargs):
        return _FakeResponse(self._status, self._payload)

    async def get(self, url, **kwargs):
        return _FakeResponse(self._status, self._payload)


class _FakeDB:
    def __init__(self):
        self.flushed = False

    async def flush(self):
        self.flushed = True


def _mock_httpx(monkeypatch, status_code: int, payload: dict):
    monkeypatch.setattr(
        oauth_tokens.httpx, "AsyncClient",
        lambda *a, **k: _FakeClient(status_code, payload),
    )


# ── Cifrado de strings ───────────────────────────────────────────────────────

class TestEncryptStr:
    def test_roundtrip(self):
        assert decrypt_str(encrypt_str("hello-token-123")) == "hello-token-123"

    def test_encrypted_is_not_plaintext(self):
        assert "sk-secret" not in encrypt_str("sk-secret")

    def test_empty_passthrough(self):
        assert encrypt_str("") == ""
        assert decrypt_str("") == ""

    def test_legacy_plaintext_passthrough(self):
        # Valor nunca cifrado (fila legacy) → se devuelve tal cual, no lanza.
        assert decrypt_str("plain_legacy_token_value") == "plain_legacy_token_value"


# ── _is_expiring ─────────────────────────────────────────────────────────────

class TestIsExpiring:
    def test_none_is_not_expiring(self):
        assert oauth_tokens._is_expiring(None) is False

    def test_far_future_is_not_expiring(self):
        assert oauth_tokens._is_expiring(datetime.now(UTC) + timedelta(hours=2)) is False

    def test_past_is_expiring(self):
        assert oauth_tokens._is_expiring(datetime.now(UTC) - timedelta(minutes=1)) is True

    def test_within_buffer_is_expiring(self):
        assert oauth_tokens._is_expiring(datetime.now(UTC) + timedelta(minutes=2)) is True

    def test_naive_datetime_treated_as_utc(self):
        past_naive = (datetime.now(UTC) - timedelta(hours=1)).replace(tzinfo=None)
        assert oauth_tokens._is_expiring(past_naive) is True


# ── ensure_valid_token ───────────────────────────────────────────────────────

class TestEnsureValidToken:
    async def test_passthrough_when_valid(self, monkeypatch):
        account = SocialAccount(
            platform="twitter",
            access_token=encrypt_str("good_token"),
            token_expires_at=datetime.now(UTC) + timedelta(hours=2),
        )

        async def _boom(_):
            raise AssertionError("no debería intentar renovar un token vigente")

        monkeypatch.setattr(oauth_tokens, "_refresh", _boom)
        token = await oauth_tokens.ensure_valid_token(account, _FakeDB())
        assert token == "good_token"

    async def test_none_when_no_token(self):
        account = SocialAccount(platform="twitter", access_token="")
        assert await oauth_tokens.ensure_valid_token(account, _FakeDB()) is None

    async def test_refreshes_rotates_and_persists(self, monkeypatch):
        account = SocialAccount(
            platform="twitter",
            access_token=encrypt_str("old_token"),
            refresh_token=encrypt_str("old_refresh"),
            token_expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        _mock_httpx(monkeypatch, 200, {
            "access_token": "new_token",
            "refresh_token": "new_refresh",
            "expires_in": 7200,
        })
        db = _FakeDB()

        token = await oauth_tokens.ensure_valid_token(account, db)

        assert token == "new_token"
        # Persistido CIFRADO (no en claro) y descifrable al valor nuevo.
        assert account.access_token != "new_token"
        assert decrypt_str(account.access_token) == "new_token"
        # Twitter rota el refresh_token → debe guardarse el nuevo.
        assert decrypt_str(account.refresh_token) == "new_refresh"
        assert account.token_expires_at > datetime.now(UTC)
        assert db.flushed is True

    async def test_none_when_refresh_http_fails(self, monkeypatch):
        account = SocialAccount(
            platform="twitter",
            access_token=encrypt_str("old_token"),
            refresh_token=encrypt_str("old_refresh"),
            token_expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        _mock_httpx(monkeypatch, 400, {"error": "invalid_grant"})
        assert await oauth_tokens.ensure_valid_token(account, _FakeDB()) is None

    async def test_none_when_expired_and_no_refresh_token(self, monkeypatch):
        # Facebook/LinkedIn sin refresh_token y token caducado → reconexión.
        account = SocialAccount(
            platform="linkedin",
            access_token=encrypt_str("old_token"),
            refresh_token=None,
            token_expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        assert await oauth_tokens.ensure_valid_token(account, _FakeDB()) is None


# ── Refresh por plataforma (wiring HTTP) ─────────────────────────────────────

class TestPlatformRefresh:
    async def test_twitter_refresh_ok(self, monkeypatch):
        account = SocialAccount(platform="twitter", refresh_token=encrypt_str("r1"))
        _mock_httpx(monkeypatch, 200, {"access_token": "at", "expires_in": 7200})
        data = await oauth_tokens._refresh_twitter(account)
        assert data["access_token"] == "at"

    async def test_facebook_refresh_uses_access_token(self, monkeypatch):
        # Facebook no tiene refresh_token: re-intercambia el access_token actual.
        account = SocialAccount(platform="facebook", access_token=encrypt_str("fb_long"))
        _mock_httpx(monkeypatch, 200, {"access_token": "fb_longer", "expires_in": 5184000})
        data = await oauth_tokens._refresh_facebook(account)
        assert data["access_token"] == "fb_longer"

    async def test_instagram_refresh_uses_access_token(self, monkeypatch):
        account = SocialAccount(platform="instagram", access_token=encrypt_str("ig_long"))
        _mock_httpx(monkeypatch, 200, {"access_token": "ig_longer", "expires_in": 5184000})
        data = await oauth_tokens._refresh_instagram(account)
        assert data["access_token"] == "ig_longer"

    async def test_twitter_refresh_returns_none_without_refresh_token(self):
        account = SocialAccount(platform="twitter", refresh_token=None)
        assert await oauth_tokens._refresh_twitter(account) is None
