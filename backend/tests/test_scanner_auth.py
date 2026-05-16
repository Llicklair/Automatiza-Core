"""Tests para app.middleware.scanner_auth — Tokens de escáner móvil."""
import time
from datetime import UTC

import jwt
import pytest
from app.core.config import settings
from app.middleware.scanner_auth import (
    create_scanner_token,
    decode_scanner_token,
    is_scanner_token,
)
from fastapi import HTTPException


class TestCreateScannerToken:
    def test_returns_dict_with_token(self):
        result = create_scanner_token("tenant-1", "user-1")
        assert "token" in result
        assert "expires_at" in result
        assert "scope" in result

    def test_token_is_decodable(self):
        result = create_scanner_token("tenant-1", "user-1")
        payload = jwt.decode(
            result["token"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert payload["sub"] == "scanner_auth"
        assert payload["tenant_id"] == "tenant-1"
        assert payload["user_id"] == "user-1"

    def test_custom_device_name(self):
        result = create_scanner_token("tenant-1", "user-1", device_name="Zebra TC21")
        payload = jwt.decode(
            result["token"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert payload["device"] == "Zebra TC21"

    def test_scope_matches_config(self):
        result = create_scanner_token("tenant-1", "user-1")
        assert result["scope"] == settings.SCANNER_ALLOWED_SCOPES

    def test_token_has_expiration(self):
        result = create_scanner_token("tenant-1", "user-1")
        payload = jwt.decode(
            result["token"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert "exp" in payload
        assert "iat" in payload


class TestDecodeScannerToken:
    def test_valid_token(self):
        result = create_scanner_token("tenant-1", "user-1")
        payload = decode_scanner_token(result["token"])
        assert payload["sub"] == "scanner_auth"
        assert payload["tenant_id"] == "tenant-1"

    def test_expired_token_raises_401(self):
        from datetime import datetime, timedelta

        expired_payload = {
            "sub": "scanner_auth",
            "tenant_id": "t-1",
            "user_id": "u-1",
            "scope": "inventory:read",
            "exp": datetime.now(UTC) - timedelta(minutes=5),
            "iat": datetime.now(UTC) - timedelta(minutes=10),
        }
        expired_token = jwt.encode(
            expired_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )
        with pytest.raises(HTTPException) as exc_info:
            decode_scanner_token(expired_token)
        assert exc_info.value.status_code == 401
        assert "expirado" in exc_info.value.detail

    def test_invalid_token_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            decode_scanner_token("not.a.valid.jwt")
        assert exc_info.value.status_code == 401
        assert "inválido" in exc_info.value.detail

    def test_non_scanner_sub_raises_403(self):
        normal_payload = {
            "sub": "regular_user",
            "tenant_id": "t-1",
            "exp": int(time.time()) + 300,
        }
        token = jwt.encode(
            normal_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )
        with pytest.raises(HTTPException) as exc_info:
            decode_scanner_token(token)
        assert exc_info.value.status_code == 403
        assert "no es de tipo scanner" in exc_info.value.detail


class TestIsScannerToken:
    def test_valid_scanner_token(self):
        from unittest.mock import MagicMock

        result = create_scanner_token("tenant-1", "user-1")
        request = MagicMock()
        request.headers = {"authorization": f"Bearer {result['token']}"}
        assert is_scanner_token(request) is True

    def test_regular_token_returns_false(self):
        from unittest.mock import MagicMock

        from app.core.security import create_access_token

        token = create_access_token({"sub": "user-123", "role": "admin"})
        request = MagicMock()
        request.headers = {"authorization": f"Bearer {token}"}
        assert is_scanner_token(request) is False

    def test_no_auth_header_returns_false(self):
        from unittest.mock import MagicMock

        request = MagicMock()
        request.headers.get = MagicMock(return_value="")
        assert is_scanner_token(request) is False

    def test_invalid_token_returns_false(self):
        from unittest.mock import MagicMock

        request = MagicMock()
        request.headers = {"authorization": "Bearer invalid.jwt.token"}
        assert is_scanner_token(request) is False

    def test_non_bearer_returns_false(self):
        from unittest.mock import MagicMock

        request = MagicMock()
        request.headers.get = lambda k, d="": "Basic dXNlcjpwYXNz" if k == "authorization" else d
        assert is_scanner_token(request) is False
