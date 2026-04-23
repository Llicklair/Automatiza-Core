"""Tests para app.core.config — Settings y validadores."""
import os

import pytest


class TestSettings:
    def test_settings_is_valid_instance(self):
        from app.core.config import Settings, settings

        assert isinstance(settings, Settings)

    def test_app_name_default(self):
        from app.core.config import settings

        assert settings.APP_NAME == "AutomatizaciónPyme"

    def test_app_version_default(self):
        from app.core.config import settings

        assert settings.APP_VERSION == "0.1.0"

    def test_algorithm_default(self):
        from app.core.config import settings

        assert settings.ALGORITHM == "HS256"

    def test_access_token_expire_minutes(self):
        from app.core.config import settings

        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 60

    def test_refresh_token_expire_days(self):
        from app.core.config import settings

        assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 30

    def test_secret_key_loaded_from_env(self):
        from app.core.config import settings

        assert settings.SECRET_KEY == os.environ["SECRET_KEY"]

    def test_environment_is_testing(self):
        from app.core.config import settings

        assert settings.ENVIRONMENT == "testing"

    def test_debug_is_true_in_test(self):
        from app.core.config import settings

        assert settings.DEBUG is True

    def test_scanner_token_expire_minutes_default(self):
        from app.core.config import settings

        assert settings.SCANNER_TOKEN_EXPIRE_MINUTES == 2

    def test_scanner_allowed_scopes_default(self):
        from app.core.config import settings

        assert "inventory:read" in settings.SCANNER_ALLOWED_SCOPES

    def test_default_llm_provider(self):
        from app.core.config import settings

        assert settings.DEFAULT_LLM_PROVIDER in (
            "claude_code", "anthropic", "gemini", "openai", "groq", "openrouter", "mock",
        )

    def test_port_default(self):
        from app.core.config import settings

        assert settings.PORT == 8080

    def test_frontend_url(self):
        from app.core.config import settings

        assert settings.FRONTEND_URL == "http://localhost:3000"


class TestSettingsValidation:
    def test_rejects_default_secret_key(self, monkeypatch):
        from app.core.config import _DEFAULT_SECRET, Settings

        monkeypatch.setenv("SECRET_KEY", _DEFAULT_SECRET)
        monkeypatch.setenv("TENANT_ENCRYPTION_KEY", os.environ["TENANT_ENCRYPTION_KEY"])
        with pytest.raises(ValueError, match="SECRET_KEY"):
            Settings()

    def test_rejects_default_encryption_key(self, monkeypatch):
        from app.core.config import _DEFAULT_ENCRYPTION, Settings

        monkeypatch.setenv("SECRET_KEY", os.environ["SECRET_KEY"])
        monkeypatch.setenv("TENANT_ENCRYPTION_KEY", _DEFAULT_ENCRYPTION)
        with pytest.raises(ValueError, match="TENANT_ENCRYPTION_KEY"):
            Settings()

    def test_current_settings_not_defaults(self):
        from app.core.config import _DEFAULT_ENCRYPTION, _DEFAULT_SECRET, settings

        assert settings.SECRET_KEY != _DEFAULT_SECRET
        assert settings.TENANT_ENCRYPTION_KEY != _DEFAULT_ENCRYPTION


class TestGetSettings:
    def test_get_settings_returns_same_instance(self):
        from app.core.config import get_settings

        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
