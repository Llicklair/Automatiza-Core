"""Regression: los handlers de error de workflows.resume y marketing (Zernio)
NO deben filtrar internals (str(e) / mensaje crudo del SDK) al cliente.

- workflows resume: except Exception -> 500 genérico, sin marcador.
- marketing connect/disconnect: except ZernioError -> 502 genérico, sin marcador.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.services.marketing.zernio_client import ZernioError

LEAK = "LEAK_MARKER_SECRET_88"


@pytest.mark.asyncio
async def test_resume_execution_does_not_leak_exception_detail(auth_client):
    workflow_id = uuid4()
    execution_id = uuid4()
    with patch(
        "app.services.workflow.service.resume_execution",
        new=AsyncMock(side_effect=Exception(LEAK)),
    ):
        resp = await auth_client.post(
            f"/api/v1/workflows/{workflow_id}/executions/{execution_id}/resume"
        )

    assert resp.status_code == 500
    assert LEAK not in resp.text
    assert LEAK not in (resp.json().get("detail") or "")


@pytest.mark.asyncio
async def test_connect_account_does_not_leak_zernio_error(auth_client):
    fake_client = AsyncMock()
    fake_client.connect_url = AsyncMock(side_effect=ZernioError(LEAK))
    with (
        patch(
            "app.api.v1.routes.marketing._pick_config",
            new=AsyncMock(return_value=SimpleNamespace(id=uuid4())),
        ),
        patch(
            "app.api.v1.routes.marketing.client_for_config",
            return_value=fake_client,
        ),
        patch(
            "app.api.v1.routes.marketing._resolve_profile_id",
            new=AsyncMock(return_value="profile-123"),
        ),
    ):
        resp = await auth_client.post("/api/v1/marketing/accounts/connect/instagram")

    assert resp.status_code == 502
    assert LEAK not in resp.text
    assert LEAK not in (resp.json().get("detail") or "")


@pytest.mark.asyncio
async def test_disconnect_account_does_not_leak_zernio_error(auth_client):
    account_id = uuid4()
    with patch(
        "app.services.marketing.social_accounts.disconnect_account",
        new=AsyncMock(side_effect=ZernioError(LEAK)),
    ):
        resp = await auth_client.delete(f"/api/v1/marketing/accounts/{account_id}")

    assert resp.status_code == 502
    assert LEAK not in resp.text
    assert LEAK not in (resp.json().get("detail") or "")
