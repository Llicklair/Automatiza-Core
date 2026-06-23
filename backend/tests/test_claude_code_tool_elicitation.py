"""Guardia DETERMINISTA de la elicitación de tools del provider `claude_code`.

POR QUÉ EXISTE (causa H, auditoría E2E 2026-06-23)
--------------------------------------------------
CI corre con ENVIRONMENT=testing → MockChatModel, que SIEMPRE devuelve tool_calls
de forma determinista. Eso oculta toda la clase de bugs del provider REAL
(`claude_code`, tool-calling basado en prompt): narrar la acción sin emitir el
bloque, mencionar la tool sin el formato correcto, rehúsa "no tengo acceso", JSON
con newlines literales. El CLI real NO existe en CI (sin binario ni suscripción),
así que aquí inyectamos salidas-CLI canónicas (las observadas en la auditoría) vía
monkeypatch de `_call_cli` y verificamos que el provider REINTENTA / PARSEA /
DEGRADA / LEVANTA correctamente. Si alguien debilita el retry o el parser, CI rojo.

El smoke con el CLI real (`test_real_cli_*`) se SALTA en CI y solo corre donde haya
binario `claude` (local/nightly) — consume cuota de la suscripción.
"""
import os
import shutil

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.core.llm.claude_code import (
    ClaudeCodeChatModel,
    LLMRefusedToolUseError,
    _is_write_tool_name,
    _parse_tool_response,
)


class _T:
    """Tool stub: solo necesita name/description/args_schema para el prompt."""

    def __init__(self, name):
        self.name = name
        self.description = "desc " + name
        self.args_schema = None


TOOLS = [_T("create_campaign"), _T("list_campaigns")]
BLOCK = (
    '<<<TOOL_CALL>>>\n{"tool_calls":[{"name":"create_campaign","arguments":{}}]}\n'
    "<<<END_TOOL_CALL>>>"
)


def _model():
    return ClaudeCodeChatModel().bind_tools(TOOLS)


def _scripted(monkeypatch, outputs):
    """Hace que `_call_cli` devuelva `outputs` en orden (una salida por llamada)."""
    it = iter(outputs)
    monkeypatch.setattr(ClaudeCodeChatModel, "_call_cli", lambda self, p: (next(it), None))


# -- elicitación / retry ----------------------------------------------------

def test_mention_then_emit_retry_fires_tool(monkeypatch):
    """Menciona la tool sin emitir el bloque → retry → emite → tool dispara."""
    _scripted(monkeypatch, ["Voy a usar create_campaign para la campana de verano.", BLOCK])
    r = _model()._generate([HumanMessage(content="crea una campana de verano")])
    tcs = r.generations[0].message.tool_calls
    assert tcs and tcs[0]["name"] == "create_campaign"


def test_mention_twice_degrades_to_text(monkeypatch):
    """Menciona la tool dos veces sin emitir → degrada a texto (no crash, no tool)."""
    _scripted(monkeypatch, ["create_campaign seria lo ideal.", "sigo describiendo: create_campaign."])
    msg = _model()._generate([HumanMessage(content="crea una campana")]).generations[0].message
    assert not msg.tool_calls and msg.content


def test_summary_after_write_no_retry(monkeypatch):
    """Tras ejecutar una ESCRITURA, un resumen que menciona la tool NO debe reintentar."""
    calls = {"n": 0}

    def fake(self, p):
        calls["n"] += 1
        return ("Hecho con create_campaign. Resumen del resultado.", None)

    monkeypatch.setattr(ClaudeCodeChatModel, "_call_cli", fake)
    _model()._generate([
        HumanMessage(content="crea una campana"),
        AIMessage(content="", tool_calls=[{"name": "create_campaign", "args": {}, "id": "1", "type": "tool_call"}]),
        ToolMessage(content="ok", tool_call_id="1", name="create_campaign"),
    ])
    assert calls["n"] == 1


def test_read_only_then_mention_write_retries(monkeypatch):
    """Solo se ejecutó una LECTURA y se narra el create → retry → write dispara."""
    _scripted(monkeypatch, ["Consulte el catalogo; ahora usaria create_campaign.", BLOCK])
    r = _model()._generate([
        HumanMessage(content="crea una campana"),
        AIMessage(content="", tool_calls=[{"name": "get_product_catalog", "args": {}, "id": "r", "type": "tool_call"}]),
        ToolMessage(content="catalogo: 10 productos", tool_call_id="r", name="get_product_catalog"),
    ])
    tcs = r.generations[0].message.tool_calls
    assert tcs and tcs[0]["name"] == "create_campaign"


def test_refusal_persists_raises(monkeypatch):
    """Rehúsa "no tengo acceso" dos veces → propaga LLMRefusedToolUseError (contrato)."""
    refusal = "create_campaign no esta disponible, no tengo acceso."
    _scripted(monkeypatch, [refusal, refusal])
    with pytest.raises(LLMRefusedToolUseError):
        _model()._generate([HumanMessage(content="crea una campana")])


def test_valid_block_parses_first_try(monkeypatch):
    _scripted(monkeypatch, [BLOCK])
    assert _model()._generate([HumanMessage(content="crea una campana")]).generations[0].message.tool_calls


# -- parser robustez --------------------------------------------------------

def test_malformed_json_literal_newline_recovers():
    """El LLM emite un newline literal dentro de un string JSON → el parser lo escapa."""
    txt = (
        '<<<TOOL_CALL>>>\n'
        '{"tool_calls":[{"name":"create_campaign","arguments":{"body":"linea1\nlinea2"}}]}\n'
        "<<<END_TOOL_CALL>>>"
    )
    msg = _parse_tool_response(txt)
    assert msg.tool_calls and msg.tool_calls[0]["name"] == "create_campaign"


def test_write_name_detection():
    assert _is_write_tool_name("create_invoice")
    assert _is_write_tool_name("update_stock")
    assert _is_write_tool_name("send_invoice_by_email")
    assert not _is_write_tool_name("list_payrolls")  # "pay" excluido a propósito
    assert not _is_write_tool_name("get_account_balance")
    assert not _is_write_tool_name("find_products")


# -- smoke con CLI real (skip en CI) ----------------------------------------

@pytest.mark.skipif(
    not (shutil.which("claude") and os.environ.get("RUN_REAL_LLM_SMOKE")),
    reason="smoke real-LLM: requiere binario claude + RUN_REAL_LLM_SMOKE=1 (solo nightly/local; "
    "consume cuota de la suscripción). En CI se salta siempre.",
)
def test_real_cli_action_does_not_crash():
    """Con el CLI real, una acción clara se procesa sin excepción (integración subprocess).
    NO asercia el tool_call (el modelo real es no-determinista); solo que el provider
    completa el ciclo. La validación behavioral va en tasks/run_one_order_real_llm.md."""
    os.environ.pop("ENVIRONMENT", None)
    r = _model()._generate([HumanMessage(content="Crea una campana de marketing llamada SmokeTest")])
    msg = r.generations[0].message
    assert msg is not None and (msg.tool_calls or isinstance(msg.content, str))
