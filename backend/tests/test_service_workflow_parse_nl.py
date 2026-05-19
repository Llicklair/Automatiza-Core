"""Tests para app.services.workflow._nlp.parse_natural_language.

El parser usa el LLM para convertir un prompt en lenguaje natural en un schema
de workflow JSON. Mockeamos `get_llm` para que los tests sean rápidos,
deterministas y no requieran API keys.
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from app.services.workflow._nlp import parse_natural_language


def _make_llm_mock(json_payload: dict, determinism: str = "false"):
    """Devuelve un objeto que imita BaseChatModel: .invoke([msgs]) -> response."""

    class _Resp:
        def __init__(self, content):
            self.content = content

    # Llamadas alternas: 1) main json llm, 2) determinism check llm
    def invoke(messages):
        return _Resp(json.dumps(json_payload))

    main_llm = SimpleNamespace(invoke=invoke)

    def invoke_det(messages):
        return _Resp(determinism)

    plain_llm = SimpleNamespace(invoke=invoke_det)

    return main_llm, plain_llm


@pytest.mark.asyncio
class TestParseNaturalLanguage:
    async def test_genera_schema_event_based(self):
        payload = {
            "trigger_type": "event_based",
            "trigger_config": {"events": ["new_email"]},
            "action_type": "send_email",
            "action_config": {"instruction": "envía un email de bienvenida"},
        }
        main, plain = _make_llm_mock(payload, "true")

        def fake_get_llm(temperature=0, format_output=None, **kw):
            return main if format_output == "json" else plain

        with patch("app.services.workflow._nlp.get_llm", side_effect=fake_get_llm):
            result = await parse_natural_language(
                "Cuando llegue un email nuevo, manda bienvenida"
            )

        assert result["trigger_type"] == "event_based"
        assert "new_email" in result["trigger_config"]["events"]
        assert result["can_be_deterministic"] is True
        # UI preview keys siempre presentes
        assert "ui_nodes" in result and "ui_edges" in result

    async def test_genera_schema_cron(self):
        payload = {
            "trigger_type": "scheduled",
            "trigger_config": {"cron": "0 9 * * 1"},
            "action_type": "ai_employee",
            "action_config": {"instruction": "lunes 9am genera el informe"},
        }
        main, plain = _make_llm_mock(payload, "false")

        def fake_get_llm(temperature=0, format_output=None, **kw):
            return main if format_output == "json" else plain

        with patch("app.services.workflow._nlp.get_llm", side_effect=fake_get_llm):
            result = await parse_natural_language("Lunes a las 9 genera informe")

        assert result["trigger_type"] == "scheduled"
        assert result["trigger_config"]["cron"] == "0 9 * * 1"
        assert result["can_be_deterministic"] is False

    async def test_acepta_respuesta_envuelta_en_markdown_json(self):
        """El LLM a veces envuelve la respuesta con ```json ... ```."""
        payload = {
            "trigger_type": "event_based",
            "trigger_config": {"events": ["any"]},
            "action_type": "noop",
            "action_config": {},
        }
        raw = "```json\n" + json.dumps(payload) + "\n```"

        class _Resp:
            content = raw

        main = SimpleNamespace(invoke=lambda msgs: _Resp())
        plain = SimpleNamespace(
            invoke=lambda msgs: SimpleNamespace(content="false")
        )

        def fake_get_llm(temperature=0, format_output=None, **kw):
            return main if format_output == "json" else plain

        with patch("app.services.workflow._nlp.get_llm", side_effect=fake_get_llm):
            result = await parse_natural_language("test")

        assert result["trigger_type"] == "event_based"
        assert "ui_nodes" in result

    async def test_falla_si_llm_devuelve_json_invalido(self):
        class _Resp:
            content = "esto no es JSON {{"

        main = SimpleNamespace(invoke=lambda msgs: _Resp())
        plain = SimpleNamespace(
            invoke=lambda msgs: SimpleNamespace(content="false")
        )

        def fake_get_llm(temperature=0, format_output=None, **kw):
            return main if format_output == "json" else plain

        with patch("app.services.workflow._nlp.get_llm", side_effect=fake_get_llm):
            with pytest.raises(json.JSONDecodeError):
                await parse_natural_language("entrada cualquiera")

    async def test_determinism_check_fallback_si_falla(self):
        """Si el check de determinismo lanza excepción, devuelve can_be_deterministic=False."""
        payload = {
            "trigger_type": "event_based",
            "trigger_config": {"events": ["x"]},
            "action_type": "ai",
            "action_config": {"instruction": "haz algo"},
        }

        class _Resp:
            content = json.dumps(payload)

        main = SimpleNamespace(invoke=lambda msgs: _Resp())

        def _broken_invoke(msgs):
            raise RuntimeError("LLM down")

        plain = SimpleNamespace(invoke=_broken_invoke)

        def fake_get_llm(temperature=0, format_output=None, **kw):
            return main if format_output == "json" else plain

        with patch("app.services.workflow._nlp.get_llm", side_effect=fake_get_llm):
            result = await parse_natural_language("test")

        assert result["can_be_deterministic"] is False
