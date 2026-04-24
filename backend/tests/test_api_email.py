"""Tests for email agent routes — POST /messaging/email/send|instruct, GET /messaging/email/status."""
import pytest
from httpx import AsyncClient


class TestEmailStatus:
    @pytest.mark.asyncio
    async def test_status_returns_configured_false_without_credentials(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/messaging/email/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "configured" in data
        assert "providers" in data
        assert data["configured"] is False
        assert data["providers"]["gmail"] is False
        assert data["providers"]["outlook"] is False
        assert data["providers"]["smtp"] is False


class TestEmailSend:
    @pytest.mark.asyncio
    async def test_send_without_credentials_returns_result(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/v1/messaging/email/send",
            json={"to": "test@example.com", "subject": "Test", "body": "Hello"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "result" in data
        # Without credentials the agent returns a SIN CREDENCIALES message, not an error
        assert isinstance(data["result"], str)

    @pytest.mark.asyncio
    async def test_send_invalid_email_returns_422(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/v1/messaging/email/send",
            json={"to": "not-an-email", "subject": "Test", "body": "Hello"},
        )
        assert resp.status_code == 422


class TestEmailInstruct:
    @pytest.mark.asyncio
    async def test_instruct_returns_success_with_mock_llm(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/v1/messaging/email/instruct",
            json={"message": "Muéstrame los correos no leídos"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "success" in data
        assert "action" in data
        assert "messages" in data
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_instruct_with_task_id(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/v1/messaging/email/instruct",
            json={"message": "Envía un resumen de facturas", "task_id": "task-123"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
