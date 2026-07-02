"""Tools reply_email_real y mark_read_real del agente email (Gmail/Outlook)."""

from unittest.mock import AsyncMock, patch

import pytest

from app.agents.email._provider_tools import build_real_tools
from app.agents.email.tools import build_tools_list

pytestmark = pytest.mark.asyncio


def _tools(providers):
    return build_real_tools(providers, imap_creds=None, default_provider=next(iter(providers)))


async def test_reply_sin_confirm_devuelve_borrador():
    *_rest, reply_tool, _mark = _tools({"gmail": "tok"})
    out = await reply_tool.coroutine(tenant_id="t", message_id="m1", body="Hola, gracias.")
    assert "Borrador" in out and "Confirmas" in out


async def test_reply_confirm_llama_cliente_gmail():
    mock_client = AsyncMock()
    # El import de GmailClient ocurre dentro de build_real_tools: patch antes de construir
    with patch("app.integrations.gmail_client.GmailClient", return_value=mock_client):
        *_rest, reply_tool, _mark = _tools({"gmail": "tok"})
        out = await reply_tool.coroutine(tenant_id="t", message_id="m1", body="ok", confirm=True)
    mock_client.reply_message.assert_awaited_once_with("m1", "ok")
    mock_client.close.assert_awaited_once()
    assert "Respuesta enviada" in out


async def test_mark_read_outlook():
    mock_client = AsyncMock()
    with patch("app.integrations.outlook_client.OutlookClient", return_value=mock_client):
        *_rest, _reply, mark_tool = _tools({"outlook": "tok"})
        out = await mark_tool.coroutine(tenant_id="t", message_id="m2")
    mock_client.mark_read.assert_awaited_once_with("m2")
    assert "marcado como leído" in out


async def test_imap_no_soporta_reply_ni_markread():
    *_rest, reply_tool, mark_tool = _tools({"imap": "x"})
    out1 = await reply_tool.coroutine(tenant_id="t", message_id="m", body="b", confirm=True)
    out2 = await mark_tool.coroutine(tenant_id="t", message_id="m")
    assert "solo está soportado" in out1
    assert "solo está soportado" in out2


async def test_build_tools_list_incluye_extra_solo_en_real():
    sin = build_tools_list()
    tools = _tools({"gmail": "tok"})
    con = build_tools_list(*tools)
    assert len(con) == len(sin) + 2
    names = [t.name for t in con]
    assert "reply_email_real" in names and "mark_read_real" in names
