"""Captura de tokens del provider claude_code → modal de consumo de IA.

Regresión del bug "el modal de consumo sale a 0": `claude -p` no reportaba
tokens. Con `--output-format json` el CLI devuelve un envelope con `result` +
`usage`; `_parse_cli_output` lo parsea y `_process_response` adjunta el
`usage_metadata` que `UsageTrackingCallback._extract_tokens` espera.
"""

from app.core.llm.claude_code import ClaudeCodeChatModel, _parse_cli_output


def test_parse_json_envelope_extracts_text_and_usage():
    raw = (
        '{"type":"result","subtype":"success","is_error":false,'
        '"result":"Hola","total_cost_usd":0.01,'
        '"usage":{"input_tokens":120,"output_tokens":45,'
        '"cache_read_input_tokens":30,"cache_creation_input_tokens":0}}'
    )
    text, usage = _parse_cli_output(raw)
    assert text == "Hola"
    # input = 120 + 30 (cache_read) + 0 (cache_creation)
    assert usage == {"input_tokens": 150, "output_tokens": 45, "total_tokens": 195}


def test_parse_plain_text_is_fallback_without_usage():
    text, usage = _parse_cli_output("respuesta en texto plano")
    assert text == "respuesta en texto plano"
    assert usage is None


def test_parse_json_without_result_key_is_text_fallback():
    raw = '{"foo": "bar"}'
    text, usage = _parse_cli_output(raw)
    assert text == raw
    assert usage is None


def test_parse_envelope_zero_usage_yields_no_meta():
    text, usage = _parse_cli_output('{"result":"ok","usage":{"input_tokens":0,"output_tokens":0}}')
    assert text == "ok"
    assert usage is None


def test_process_response_attaches_usage_metadata_to_message():
    m = ClaudeCodeChatModel()
    meta = {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}
    res = m._process_response("texto", meta)
    msg = res.generations[0].message
    assert msg.usage_metadata == meta


def test_process_response_without_usage_leaves_metadata_unset():
    m = ClaudeCodeChatModel()
    res = m._process_response("texto", None)
    assert res.generations[0].message.usage_metadata is None
