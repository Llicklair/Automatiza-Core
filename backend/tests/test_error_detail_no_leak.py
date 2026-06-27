"""Regresión L2 (info-disclosure): el `detail` de un 500 no debe filtrar el
mensaje de una excepción INESPERADA al cliente.

Para cada endpoint cubierto, mockeamos el servicio interno para que lance una
excepción con un MARCADOR único. Aserción: la respuesta es 500 Y el body NO
contiene el marcador (es un mensaje genérico de dominio). El detalle completo
sigue yendo a los logs (logger.exception / logger.error), pero nunca al cliente.
"""
from unittest.mock import AsyncMock, patch

import pytest

LEAK_MARKER = "LEAK_MARKER_SECRET_42"


@pytest.mark.asyncio
async def test_generative_ui_generate_no_leak(auth_client):
    """POST /generative-ui/generate: excepción inesperada → 500 genérico, sin fuga."""
    with patch(
        "app.api.v1.routes.generative_ui.svc.generate_ui",
        side_effect=RuntimeError(LEAK_MARKER),
    ):
        resp = await auth_client.post(
            "/api/v1/generative-ui/generate",
            json={"prompt": "haz una tabla"},
        )

    assert resp.status_code == 500
    assert LEAK_MARKER not in resp.text
    assert LEAK_MARKER not in (resp.json().get("detail") or "")


@pytest.mark.asyncio
async def test_messaging_draft_reply_no_leak(auth_client):
    """POST /messaging/email/draft-reply: excepción inesperada → 500 genérico, sin fuga.

    El endpoint solo llega a `draft_reply` si encuentra un mensaje vía proveedor,
    así que mockeamos `get_oauth_token` (token gmail) y `GmailClient` (devuelve un
    mensaje) para alcanzar la rama de IA, donde `draft_reply` lanza el marcador.
    """

    class _FakeGmailClient:
        def __init__(self, token):
            pass

        async def get_message(self, message_id):
            return {"id": message_id, "subject": "hola", "body": "texto"}

        async def close(self):
            return None

    with (
        patch(
            "app.services.email.credentials.get_oauth_token",
            new=AsyncMock(side_effect=lambda tenant, provider: "tok" if provider == "gmail" else None),
        ),
        patch("app.integrations.gmail_client.GmailClient", _FakeGmailClient),
        patch(
            "app.services.email_ai.draft_reply",
            side_effect=RuntimeError(LEAK_MARKER),
        ),
    ):
        resp = await auth_client.post(
            "/api/v1/messaging/email/draft-reply",
            json={"message_id": "abc123"},
        )

    assert resp.status_code == 500
    assert LEAK_MARKER not in resp.text
    assert LEAK_MARKER not in (resp.json().get("detail") or "")


@pytest.mark.asyncio
async def test_templates_preview_no_leak(auth_client):
    """POST /templates/preview: excepción inesperada → 500 genérico, sin fuga."""
    with patch(
        "app.api.v1.routes.templates.svc.generate_preview",
        side_effect=RuntimeError(LEAK_MARKER),
    ):
        resp = await auth_client.post(
            "/api/v1/templates/preview",
            json={},
        )

    assert resp.status_code == 500
    assert LEAK_MARKER not in resp.text
    assert LEAK_MARKER not in (resp.json().get("detail") or "")


@pytest.mark.asyncio
async def test_messaging_classify_no_leak(auth_client):
    """POST /messaging/email/classify: excepción inesperada → 500 genérico, sin fuga."""
    with patch(
        "app.services.email_ai.classify_messages",
        side_effect=RuntimeError(LEAK_MARKER),
    ):
        resp = await auth_client.post(
            "/api/v1/messaging/email/classify",
            json={
                "messages": [
                    {"id": "1", "from": "a@b.com", "subject": "hola", "snippet": "test"}
                ]
            },
        )

    assert resp.status_code == 500
    assert LEAK_MARKER not in resp.text
    assert LEAK_MARKER not in (resp.json().get("detail") or "")
