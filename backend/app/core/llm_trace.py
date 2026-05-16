"""
Callback que registra cada llamada LLM en un fichero JSONL para debug
post-mortem. Activable con la env var `LLM_TRACE_ENABLED=true`.

Cubre todos los providers (BaseChatModel respeta callbacks): Anthropic,
OpenAI, Groq, OpenRouter, ClaudeCodeChatModel y MockChatModel.

Cada llamada genera 2 ó 3 líneas en el JSONL diario:
  - "chat_start" — mensajes de entrada, tools disponibles, model, run_id
  - "chat_end"   — latencia, response, tool_calls hechos, tokens
  - "chat_error" — si la llamada falla (timeout, parseo, rate limit)

Comparten run_id para agrupar.

Diseño defensivo: cualquier excepción dentro del callback se traga;
el logging NUNCA debe romper la llamada al LLM real.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

_log = logging.getLogger(__name__)

_DEFAULT_DIR = Path("logs/llm")
_MAX_CONTENT = int(os.environ.get("LLM_TRACE_MAX_CONTENT", "8000"))


def _truncate(value: Any, limit: int = _MAX_CONTENT) -> Any:
    """Recorta strings largos preservando un sufijo legible."""
    if not isinstance(value, str):
        return value
    if len(value) <= limit:
        return value
    return value[:limit] + f"…[+{len(value) - limit} chars truncated]"


def _serialize_message(msg: Any) -> dict[str, Any]:
    """Convierte un BaseMessage a dict serializable, tolerando tipos raros."""
    cls = msg.__class__.__name__
    out: dict[str, Any] = {"type": cls}
    content = getattr(msg, "content", None)
    if content is not None:
        if isinstance(content, list):
            # Anthropic content blocks (text, tool_use, image…)
            out["content"] = [_truncate(json.dumps(b, default=str)) for b in content]
        else:
            out["content"] = _truncate(str(content))
    tool_calls = getattr(msg, "tool_calls", None)
    if tool_calls:
        out["tool_calls"] = [
            {
                "name": tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None),
                "args": _truncate(
                    json.dumps(
                        tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", {}),
                        default=str,
                    )
                ),
                "id": tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None),
            }
            for tc in tool_calls
        ]
    tcid = getattr(msg, "tool_call_id", None)
    if tcid:
        out["tool_call_id"] = tcid
    return out


def _serialized_model_name(serialized: dict[str, Any] | None) -> str:
    if not serialized:
        return "unknown"
    name = serialized.get("name")
    if name:
        return name
    sid = serialized.get("id") or []
    if isinstance(sid, list) and sid:
        return str(sid[-1])
    return "unknown"


class LLMTraceCallback(BaseCallbackHandler):
    """Escribe un JSONL por día con cada llamada LLM."""

    def __init__(self, log_dir: Path | str = _DEFAULT_DIR) -> None:
        super().__init__()
        self.log_dir = Path(log_dir)
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            _log.warning("No se pudo crear %s: %s — trace queda inactivo", self.log_dir, e)
        self._starts: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    # ── helpers ─────────────────────────────────────────────────────────

    def _today_path(self) -> Path:
        return self.log_dir / f"{datetime.now(UTC).date().isoformat()}.jsonl"

    def _write(self, record: dict[str, Any]) -> None:
        record.setdefault("ts", datetime.now(UTC).isoformat())
        try:
            line = json.dumps(record, ensure_ascii=False, default=str)
        except Exception as e:
            _log.debug("LLMTraceCallback: no se pudo serializar record: %s", e)
            return
        try:
            with self._lock:
                with self._today_path().open("a", encoding="utf-8") as f:
                    f.write(line + "\n")
        except OSError as e:
            _log.debug("LLMTraceCallback: error escribiendo JSONL: %s", e)

    # ── start ───────────────────────────────────────────────────────────

    def on_chat_model_start(
        self,
        serialized: dict[str, Any] | None,
        messages: list,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        invocation_params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        try:
            run_key = str(run_id)
            self._starts[run_key] = {"t0": time.monotonic()}
            flat: list[dict[str, Any]] = []
            for batch in messages or []:
                for m in batch:
                    flat.append(_serialize_message(m))
            tools_meta = []
            inv = invocation_params or kwargs.get("invocation_params") or {}
            for t in inv.get("tools", []) or []:
                if isinstance(t, dict):
                    tools_meta.append(
                        t.get("function", {}).get("name") or t.get("name") or "?"
                    )
                else:
                    tools_meta.append(getattr(t, "name", "?"))
            self._write(
                {
                    "event": "chat_start",
                    "run_id": run_key,
                    "parent_run_id": str(parent_run_id) if parent_run_id else None,
                    "model": _serialized_model_name(serialized),
                    "tags": list(tags or []),
                    "metadata": dict(metadata or {}),
                    "tools_available": tools_meta,
                    "messages": flat,
                }
            )
        except Exception as e:
            _log.debug("LLMTraceCallback.on_chat_model_start error: %s", e)

    # Para LLMs no-chat (legacy) — caen aquí; capturamos lo posible.
    def on_llm_start(
        self,
        serialized: dict[str, Any] | None,
        prompts: list[str],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        try:
            run_key = str(run_id)
            self._starts[run_key] = {"t0": time.monotonic()}
            self._write(
                {
                    "event": "llm_start",
                    "run_id": run_key,
                    "parent_run_id": str(parent_run_id) if parent_run_id else None,
                    "model": _serialized_model_name(serialized),
                    "tags": list(tags or []),
                    "metadata": dict(metadata or {}),
                    "prompts": [_truncate(p) for p in (prompts or [])],
                }
            )
        except Exception as e:
            _log.debug("LLMTraceCallback.on_llm_start error: %s", e)

    # ── end ─────────────────────────────────────────────────────────────

    def on_llm_end(self, response: LLMResult, *, run_id: UUID, **kwargs: Any) -> None:
        try:
            run_key = str(run_id)
            t0 = self._starts.pop(run_key, {}).get("t0")
            latency_s = round(time.monotonic() - t0, 3) if t0 else None
            generations = []
            for batch in response.generations or []:
                for gen in batch:
                    text = getattr(gen, "text", "") or ""
                    msg = getattr(gen, "message", None)
                    entry: dict[str, Any] = {"text": _truncate(text)}
                    if msg is not None:
                        ser = _serialize_message(msg)
                        if "tool_calls" in ser:
                            entry["tool_calls"] = ser["tool_calls"]
                    info = getattr(gen, "generation_info", None) or {}
                    if info.get("finish_reason"):
                        entry["finish_reason"] = info["finish_reason"]
                    generations.append(entry)
            tokens = (response.llm_output or {}).get("token_usage") or (
                response.llm_output or {}
            ).get("usage")
            self._write(
                {
                    "event": "chat_end",
                    "run_id": run_key,
                    "latency_s": latency_s,
                    "tokens": tokens,
                    "generations": generations,
                }
            )
        except Exception as e:
            _log.debug("LLMTraceCallback.on_llm_end error: %s", e)

    # ── error ───────────────────────────────────────────────────────────

    def on_llm_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        try:
            run_key = str(run_id)
            t0 = self._starts.pop(run_key, {}).get("t0")
            latency_s = round(time.monotonic() - t0, 3) if t0 else None
            self._write(
                {
                    "event": "chat_error",
                    "run_id": run_key,
                    "latency_s": latency_s,
                    "error_type": type(error).__name__,
                    "error": _truncate(str(error), limit=2000),
                }
            )
        except Exception as e:
            _log.debug("LLMTraceCallback.on_llm_error error: %s", e)


# ── Singleton ──────────────────────────────────────────────────────────

_INSTANCE: LLMTraceCallback | None = None


def is_enabled() -> bool:
    return os.environ.get("LLM_TRACE_ENABLED", "").lower() in ("1", "true", "yes", "on")


def get_trace_callback() -> LLMTraceCallback | None:
    """Devuelve la instancia compartida si LLM_TRACE_ENABLED, si no None."""
    if not is_enabled():
        return None
    global _INSTANCE
    if _INSTANCE is None:
        log_dir = os.environ.get("LLM_TRACE_DIR", str(_DEFAULT_DIR))
        _INSTANCE = LLMTraceCallback(log_dir=log_dir)
    return _INSTANCE


def attach_to(llm: Any) -> Any:
    """Inyecta el trace callback a un BaseChatModel sin pisar otros callbacks.

    Tolera tipos raros (modelos custom, RunnableBinding) — devuelve el llm
    sin tocar si no se puede adjuntar.
    """
    cb = get_trace_callback()
    if cb is None:
        return llm
    try:
        existing = list(getattr(llm, "callbacks", None) or [])
        if cb in existing:
            return llm
        existing.append(cb)
        llm.callbacks = existing
    except Exception as e:
        _log.debug("LLMTraceCallback: no se pudo adjuntar al LLM (%s)", e)
    return llm
