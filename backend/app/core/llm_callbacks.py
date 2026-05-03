"""
Callback de LangChain para tracking de uso de tokens por tenant/agente.
Se inyecta en el config del grafo LangGraph y se propaga automáticamente
a todos los nodos y herramientas sin modificar los agentes individuales.
"""

import logging
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from app.core.config import settings
from app.services import llm_usage_tracker

_log = logging.getLogger(__name__)


class UsageTrackingCallback(BaseCallbackHandler):
    """
    Captura tokens de cada llamada LLM y los registra en llm_usage_tracker.

    Detecta el provider activo inspeccionando el serialized dict que LangChain
    pasa en on_llm_start. Funciona con ChatAnthropic, ChatOpenAI, ChatGroq, etc.
    """

    def __init__(self, tenant_id: str, agent_name: str = "unknown") -> None:
        super().__init__()
        self.tenant_id = tenant_id
        self.agent_name = agent_name
        self._current_provider: str = "unknown"
        # Accumulated totals for the lifetime of this callback instance (one task run)
        self.total_tokens_in: int = 0
        self.total_tokens_out: int = 0
        self.total_cost_usd: float = 0.0

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        **kwargs: Any,
    ) -> None:
        # Inferir provider del nombre de clase del LLM
        name = (serialized.get("name") or serialized.get("id", [""])[-1] or "").lower()
        if "anthropic" in name:
            self._current_provider = "anthropic"
        elif "openai" in name:
            self._current_provider = "openai"
        elif "groq" in name:
            self._current_provider = "groq"
        elif "mock" in name:
            self._current_provider = "mock"
        else:
            self._current_provider = "unknown"

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list,
        **kwargs: Any,
    ) -> None:
        # on_chat_model_start también recibe serialized — misma lógica
        self.on_llm_start(serialized, [], **kwargs)

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        try:
            tokens_in, tokens_out = _extract_tokens(response)
            if tokens_in + tokens_out > 0:
                llm_usage_tracker.record(
                    tenant_id=self.tenant_id,
                    agent=self.agent_name,
                    provider=self._current_provider,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                )
                self.total_tokens_in += tokens_in
                self.total_tokens_out += tokens_out
                self.total_cost_usd += llm_usage_tracker.estimate_cost(
                    self._current_provider, tokens_in, tokens_out
                )
        except Exception as exc:
            _log.debug("UsageTrackingCallback.on_llm_end error: %s", exc)


def get_langfuse_callback(
    tenant_id: str,
    agent: str = "unknown",
    task_id: str | None = None,
) -> BaseCallbackHandler | None:
    """Devuelve un CallbackHandler de Langfuse listo para enchufar a LangChain
    si: (a) langfuse está instalado en el venv, y (b) las dos keys
    LANGFUSE_PUBLIC_KEY/SECRET_KEY están configuradas. Sino devuelve None.

    Cuando devuelve un handler, LangChain envía cada llamada LLM (input
    messages, output, tokens, latencia) a Langfuse Cloud, agrupada por
    user_id=tenant_id y con metadata del agente.

    Diseño: degradación silenciosa total. Activar Langfuse es solo añadir
    `langfuse` al venv + las keys al .env; el código no cambia.
    """
    if not (settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY):
        return None

    try:
        from langfuse.callback import CallbackHandler
    except ImportError:
        _log.debug(
            "Langfuse keys configuradas pero el paquete no está instalado. "
            "pip install langfuse — o no usar observability extra."
        )
        return None

    try:
        return CallbackHandler(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
            user_id=tenant_id or "unknown",
            session_id=task_id,
            metadata={"agent": agent, "tenant_id": tenant_id},
        )
    except Exception as exc:
        _log.warning("Langfuse handler init falló: %s", exc)
        return None


def _extract_tokens(response: LLMResult) -> tuple[int, int]:
    """
    Extrae (tokens_in, tokens_out) de un LLMResult.
    Prueba múltiples ubicaciones para compatibilidad con todos los providers.
    """
    # 1. llm_output["token_usage"] — OpenAI estándar
    usage = (response.llm_output or {}).get("token_usage") or {}
    if usage:
        return (
            int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
            int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
        )

    # 2. usage_metadata en el AIMessage del primer generation — LangChain 0.3+
    try:
        gen = response.generations[0][0]
        meta = getattr(gen.message, "usage_metadata", None) or {}
        if meta:
            return (
                int(meta.get("input_tokens") or 0),
                int(meta.get("output_tokens") or 0),
            )
    except (IndexError, AttributeError):
        pass

    # 3. Anthropic específico en llm_output["usage"]
    usage2 = (response.llm_output or {}).get("usage") or {}
    if usage2:
        return (
            int(usage2.get("input_tokens") or 0),
            int(usage2.get("output_tokens") or 0),
        )

    return 0, 0
