"""Tests para app.core.dependencies — Inyección de dependencias FastAPI."""
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.core.dependencies import get_current_user, require_role
from app.core.security import create_access_token


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self, db: AsyncSession, seed_tenant_and_user):
        tenant, user, token = seed_tenant_and_user
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        result = await get_current_user(credentials=creds, db=db)
        assert result.id == user.id
        assert result.email == "test@empresa.com"

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self, db: AsyncSession):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid.jwt.token")
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds, db=db)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_nonexistent_user_raises_401(self, db: AsyncSession, seed_tenant_and_user):
        tenant, user, _ = seed_tenant_and_user
        fake_user_id = str(uuid4())
        token = create_access_token({
            "sub": fake_user_id,
            "tenant_id": str(tenant.id),
            "role": "admin",
        })
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds, db=db)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_inactive_user_raises_401(self, db: AsyncSession, seed_tenant_and_user):
        tenant, user, token = seed_tenant_and_user
        # Deactivate the user
        user.is_active = False
        await db.commit()

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds, db=db)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_token_without_sub_raises_401(self, db: AsyncSession):
        token = create_access_token({"tenant_id": "some-id", "role": "admin"})
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds, db=db)
        assert exc_info.value.status_code == 401


class TestRequireRole:
    @pytest.mark.asyncio
    async def test_matching_role_passes(self, db: AsyncSession, seed_tenant_and_user):
        tenant, user, token = seed_tenant_and_user
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        resolved_user = await get_current_user(credentials=creds, db=db)

        checker = require_role("admin", "superadmin")
        result = await checker(current_user=resolved_user)
        assert result.id == user.id

    @pytest.mark.asyncio
    async def test_non_matching_role_raises_403(self, db: AsyncSession, seed_tenant_and_user):
        tenant, user, token = seed_tenant_and_user
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        resolved_user = await get_current_user(credentials=creds, db=db)

        checker = require_role("superadmin")
        with pytest.raises(HTTPException) as exc_info:
            await checker(current_user=resolved_user)
        assert exc_info.value.status_code == 403
        assert "superadmin" in exc_info.value.detail
