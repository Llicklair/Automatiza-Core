"""Tests para los endpoints de autenticación /api/v1/auth/*."""
import pytest
from httpx import AsyncClient


class TestRegister:
    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        payload = {
            "email": "nuevo@empresa.com",
            "password": "Password123!",
            "full_name": "Nuevo Usuario",
            "tenant": {
                "name": "Mi Empresa S.L.",
                "nif": "B99887766",
            },
        }
        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "nuevo@empresa.com"
        assert data["role"] == "admin"
        assert data["is_active"] is True
        assert "id" in data
        assert "tenant_id" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient):
        payload = {
            "email": "dup@empresa.com",
            "password": "Password123!",
            "full_name": "User",
            "tenant": {"name": "Empresa A", "nif": "A11223344"},
        }
        resp1 = await client.post("/api/v1/auth/register", json=payload)
        assert resp1.status_code == 201

        # Mismo email, distinto NIF
        payload["tenant"] = {"name": "Empresa B", "nif": "B11223344"}
        resp2 = await client.post("/api/v1/auth/register", json=payload)
        assert resp2.status_code == 400
        assert "email" in resp2.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_duplicate_nif(self, client: AsyncClient):
        payload1 = {
            "email": "user1@test.com",
            "password": "Password123!",
            "full_name": "User 1",
            "tenant": {"name": "Empresa X", "nif": "X12345678"},
        }
        resp1 = await client.post("/api/v1/auth/register", json=payload1)
        assert resp1.status_code == 201

        payload2 = {
            "email": "user2@test.com",
            "password": "Password123!",
            "full_name": "User 2",
            "tenant": {"name": "Empresa Y", "nif": "X12345678"},  # mismo NIF
        }
        resp2 = await client.post("/api/v1/auth/register", json=payload2)
        assert resp2.status_code == 400
        assert "nif" in resp2.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_invalid_nif_format(self, client: AsyncClient):
        payload = {
            "email": "test@test.com",
            "password": "Password123!",
            "full_name": "Test",
            "tenant": {"name": "Empresa", "nif": "123"},  # NIF inválido
        }
        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 422  # Validación Pydantic

    @pytest.mark.asyncio
    async def test_register_short_password(self, client: AsyncClient):
        payload = {
            "email": "test@test.com",
            "password": "short",
            "full_name": "Test",
            "tenant": {"name": "Empresa", "nif": "B12345678"},
        }
        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 422


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient):
        # Primero registrar
        await client.post("/api/v1/auth/register", json={
            "email": "login@test.com",
            "password": "MiPass123!",
            "full_name": "Login User",
            "tenant": {"name": "Empresa Login", "nif": "L12345678"},
        })

        resp = await client.post("/api/v1/auth/login", json={
            "email": "login@test.com",
            "password": "MiPass123!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient):
        await client.post("/api/v1/auth/register", json={
            "email": "wrong@test.com",
            "password": "CorrectPass1!",
            "full_name": "User",
            "tenant": {"name": "Empresa", "nif": "W12345678"},
        })

        resp = await client.post("/api/v1/auth/login", json={
            "email": "wrong@test.com",
            "password": "WrongPass1!",
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_email(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "noexiste@test.com",
            "password": "Whatever123!",
        })
        assert resp.status_code == 401


class TestRefresh:
    @pytest.mark.asyncio
    async def test_refresh_success(self, client: AsyncClient):
        # Registrar + login
        await client.post("/api/v1/auth/register", json={
            "email": "refresh@test.com",
            "password": "RefreshPass1!",
            "full_name": "Refresh User",
            "tenant": {"name": "Empresa Refresh", "nif": "R12345678"},
        })
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "refresh@test.com",
            "password": "RefreshPass1!",
        })
        refresh_token = login_resp.json()["refresh_token"]

        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": "token.invalido.aqui",
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_with_access_token_fails(self, client: AsyncClient):
        """No se puede usar un access_token como refresh_token."""
        await client.post("/api/v1/auth/register", json={
            "email": "norefresh@test.com",
            "password": "NoRefresh1!",
            "full_name": "User",
            "tenant": {"name": "Empresa NR", "nif": "N12345678"},
        })
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "norefresh@test.com",
            "password": "NoRefresh1!",
        })
        access_token = login_resp.json()["access_token"]

        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": access_token,  # access, no refresh
        })
        assert resp.status_code == 401
