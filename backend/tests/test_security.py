"""Tests para app.core.security — hashing, tokens JWT."""
import time
from datetime import timedelta

import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "MiContraseña_Segura!123"
        hashed = get_password_hash(password)
        assert hashed != password
        assert verify_password(password, hashed)

    def test_wrong_password_fails(self):
        hashed = get_password_hash("correcta")
        assert not verify_password("incorrecta", hashed)

    def test_different_hashes_for_same_password(self):
        """bcrypt genera salt aleatorio → hashes distintos."""
        h1 = get_password_hash("misma")
        h2 = get_password_hash("misma")
        assert h1 != h2

    def test_empty_password(self):
        hashed = get_password_hash("")
        assert verify_password("", hashed)
        assert not verify_password("algo", hashed)

    def test_unicode_password(self):
        password = "contraseña_con_ñ_y_€"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed)


class TestAccessToken:
    def test_create_and_decode(self):
        data = {"sub": "user-123", "tenant_id": "tenant-456", "role": "admin"}
        token = create_access_token(data)
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["sub"] == "user-123"
        assert decoded["tenant_id"] == "tenant-456"
        assert decoded["role"] == "admin"
        assert decoded["type"] == "access"

    def test_custom_expiry(self):
        data = {"sub": "user-1"}
        token = create_access_token(data, expires_delta=timedelta(minutes=5))
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["sub"] == "user-1"

    def test_expired_token_returns_none(self):
        data = {"sub": "user-1"}
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))
        assert decode_token(token) is None

    def test_invalid_token_returns_none(self):
        assert decode_token("esto.no.es.un.token.valido") is None
        assert decode_token("") is None
        assert decode_token("abc123") is None


class TestRefreshToken:
    def test_create_and_decode(self):
        data = {"sub": "user-1", "tenant_id": "t-1", "role": "user"}
        token = create_refresh_token(data)
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["type"] == "refresh"
        assert decoded["sub"] == "user-1"

    def test_refresh_token_differs_from_access(self):
        data = {"sub": "user-1", "tenant_id": "t-1", "role": "admin"}
        access = create_access_token(data)
        refresh = create_refresh_token(data)
        assert access != refresh
