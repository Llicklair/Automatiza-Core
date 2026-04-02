"""
ClaudeCodeChatModel — LangChain wrapper para Claude Code CLI (suscripción VSCode/Pro).

Estrategia: warm process pool por tenant.
  - Un proceso `claude -p` pre-spawneado por tenant espera en stdin.
  - Al usarse, se lanza inmediatamente un reemplazo en background.
  - Cold start solo en la primera llamada; las siguientes usan el proceso ya cargado.
  - cwd neutro (home del usuario) para evitar cargar el contexto del proyecto.

Tool calling: prompt-based.
  - bind_tools() almacena los schemas y devuelve un clon.
  - Se inyecta un system prompt pidiendo formato <<<TOOL_CALL>>> JSON.
  - Se parsea la respuesta para construir AIMessage.tool_calls reales.
  - tools_condition + ToolNode de LangGraph funcionan sin cambios.
"""
import asyncio
import json
import logging
import os
import re
import shutil
import uuid
from typing import Any, List, Optional

from pydantic import ConfigDict
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableLambda

_log = logging.getLogger(__name__)

TIMEOUT = 180  # segundos

# ---------------------------------------------------------------------------
# Warm process pool
# ---------------------------------------------------------------------------
_warm_pool: dict[str, "asyncio.subprocess.Process"] = {}
_refill_in_flight: set[str] = set()


def _resolve_claude_bin() -> str:
    env_bin = os.environ.get("CLAUDE_CODE_BIN")
    if env_bin and os.path.isfile(env_bin):
        return env_bin
    found = shutil.which("claude")
    if found:
        return found
    for candidate in [
        os.path.expanduser("~/.local/bin/claude"),
        os.path.expandvars("%APPDATA%/npm/claude.cmd"),
        os.path.expandvars("%APPDATA%/npm/claude"),
    ]:
        if os.path.isfile(candidate):
            return candidate
    return "claude"


def _clean_env() -> dict:
    env = os.environ.copy()
    for key in ("CLAUDECODE", "CLAUDE_CODE_SESSION", "CLAUDE_CODE_ENTRYPOINT"):
        env.pop(key, None)
    return env


def _neutral_cwd() -> str:
    """Directorio temporal sin CLAUDE.md — evita que el CLI cargue el contexto del proyecto."""
    import tempfile
    return tempfile.gettempdir()


async def _spawn_process() -> "asyncio.subprocess.Process":
    return await asyncio.create_subprocess_exec(
        _resolve_claude_bin(), "-p", "--dangerously-skip-permissions",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=_clean_env(),
        cwd=_neutral_cwd(),
    )


async def _refill_slot(key: str) -> None:
    try:
        proc = await _spawn_process()
        _warm_pool[key] = proc
        _log.debug("[ClaudeCode] slot '%s' pre-calentado (pid=%s)", key, proc.pid)
    except Exception as exc:
        _log.warning("[ClaudeCode] pre-calentamiento fallido para '%s': %s", key, exc)
    finally:
        _refill_in_flight.discard(key)


async def _acquire_process(key: str) -> "asyncio.subprocess.Process":
    proc = _warm_pool.pop(key, None)

    # Lanzar refill en background
    if key not in _refill_in_flight:
        _refill_in_flight.add(key)
        asyncio.create_task(_refill_slot(key))

    if proc is not None and proc.returncode is not None:
        _log.warning("[ClaudeCode] proceso warm muerto para '%s', spawneando fresh", key)
        proc = None

    if proc is None:
        _log.info("[ClaudeCode] pool miss para '%s' — cold start", key)
        proc = await _spawn_process()
    else:
        _log.info("[ClaudeCode] pool hit para '%s' — warm start (pid=%s)", key, proc.pid)

    return proc


# ---------------------------------------------------------------------------
# Tool schema helpers
# ---------------------------------------------------------------------------

_TOOL_CALL_START = "<<<TOOL_CALL>>>"
_TOOL_CALL_END = "<<<END_TOOL_CALL>>>"
_TOOL_CALL_RE = re.compile(
    re.escape(_TOOL_CALL_START) + r"\s*(.*?)\s*" + re.escape(_TOOL_CALL_END),
    re.DOTALL,
)
# Fallback: detectar JSON suelto con tool_calls (sin marcadores)
_BARE_JSON_RE = re.compile(
    r'\{\s*"tool_calls"\s*:\s*\[.*?\]\s*\}',
    re.DOTALL,
)
# Fallback: JSON envuelto en markdown ```json ... ```
_MARKDOWN_JSON_RE = re.compile(
    r"```(?:json)?\s*(\{.*?\})\s*```",
    re.DOTALL,
)


def _tools_to_schema(tools) -> list[dict]:
    """Convierte lista de LangChain @tool objects a schemas simplificados para el prompt."""
    schemas = []
    for t in tools:
        schema: dict[str, Any] = {"name": t.name, "description": t.description or ""}
        if hasattr(t, "args_schema") and t.args_schema is not None:
            if hasattr(t.args_schema, "model_json_schema"):
                raw = t.args_schema.model_json_schema()
            elif hasattr(t.args_schema, "schema"):
                raw = t.args_schema.schema()
            else:
                raw = {}
            # Simplificar: solo name, type, required — eliminar ruido
            props = raw.get("properties", {})
            required = set(raw.get("required", []))
            simple_params = {}
            for pname, pinfo in props.items():
                p: dict[str, Any] = {"type": pinfo.get("type", "string")}
                if pinfo.get("description"):
                    p["description"] = pinfo["description"]
                if pinfo.get("default") is not None and pinfo.get("default") != "":
                    p["default"] = pinfo["default"]
                if pinfo.get("enum"):
                    p["enum"] = pinfo["enum"]
                if pname in required:
                    p["required"] = True
                simple_params[pname] = p
            schema["parameters"] = simple_params
        schemas.append(schema)
    return schemas


def _build_tool_system_prompt(tools) -> str:
    """Genera el system prompt que instruye al LLM a usar el formato de tool calling."""
    schemas = _tools_to_schema(tools)
    schemas_json = json.dumps(schemas, ensure_ascii=False, indent=2)

    # Generar ejemplo concreto con la primera tool disponible
    example_tool = schemas[0] if schemas else {"name": "example_tool", "parameters": {"arg1": {}}}
    example_name = example_tool["name"]
    example_args = {}
    for pname, pinfo in example_tool.get("parameters", {}).items():
        ptype = pinfo.get("type", "string")
        if pinfo.get("default") is not None and pinfo.get("default") != "":
            example_args[pname] = pinfo["default"]
        elif ptype == "number" or ptype == "float":
            example_args[pname] = 0
        elif ptype == "integer":
            example_args[pname] = 0
        elif ptype == "boolean":
            example_args[pname] = True
        else:
            example_args[pname] = f"valor_{pname}"

    return (
        "# TOOL CALLING PROTOCOL\n\n"
        "You have tools available. To use them, respond with ONLY this exact format:\n\n"
        f"{_TOOL_CALL_START}\n"
        '{"tool_calls": [{"name": "TOOL_NAME", "arguments": {"param": "value"}}]}\n'
        f"{_TOOL_CALL_END}\n\n"
        "## RULES (CRITICAL — follow exactly):\n"
        f"1. ONLY output the {_TOOL_CALL_START}...{_TOOL_CALL_END} block. "
        "NO text before, NO text after, NO markdown fences.\n"
        "2. If you do NOT need a tool, respond with plain text (no markers).\n"
        "3. ALL parameter values must be the correct type (string, number, boolean).\n"
        "4. Include ALL required parameters. Omit optional ones unless the user specified them.\n"
        "5. Use EXACT tool names from the list below.\n"
        "6. For multiple tools, put them all in one tool_calls array.\n\n"
        f"## EXAMPLE — calling {example_name}:\n"
        f"{_TOOL_CALL_START}\n"
        f'{json.dumps({"tool_calls": [{"name": example_name, "arguments": example_args}]}, ensure_ascii=False)}\n'
        f"{_TOOL_CALL_END}\n\n"
        f"## Available tools:\n{schemas_json}"
    )


def _extract_json_from_text(text: str) -> Optional[str]:
    """Intenta extraer JSON de tool_calls usando múltiples estrategias de parseo."""
    # 1. Marcadores explícitos (más fiable)
    match = _TOOL_CALL_RE.search(text)
    if match:
        return match.group(1).strip()

    # 2. JSON envuelto en markdown ```json ... ```
    match = _MARKDOWN_JSON_RE.search(text)
    if match:
        raw = match.group(1).strip()
        if '"tool_calls"' in raw:
            return raw

    # 3. JSON suelto con tool_calls (Claude omitió los marcadores)
    match = _BARE_JSON_RE.search(text)
    if match:
        return match.group(0).strip()

    return None


def _parse_tool_response(text: str) -> AIMessage:
    """Parsea la respuesta del CLI buscando tool calls con múltiples estrategias."""
    raw_json = _extract_json_from_text(text)
    if raw_json is None:
        return AIMessage(content=text)

    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as e:
        _log.warning("[ClaudeCode] JSON malformado en tool_call, fallback a texto: %s", e)
        return AIMessage(content=text)

    raw_calls = parsed.get("tool_calls") if isinstance(parsed, dict) else None
    if not raw_calls or not isinstance(raw_calls, list):
        _log.warning("[ClaudeCode] Estructura tool_calls inválida, fallback a texto")
        return AIMessage(content=text)

    tool_calls = []
    for tc in raw_calls:
        if not isinstance(tc, dict) or "name" not in tc:
            continue
        args = tc.get("arguments") or tc.get("args") or {}
        # Coerce: si un valor debería ser string pero vino como número, convertir
        tool_calls.append({
            "name": tc["name"],
            "args": {k: str(v) if isinstance(v, bool) and not isinstance(v, int) else v
                     for k, v in args.items()},
            "id": f"call_{uuid.uuid4().hex[:8]}",
            "type": "tool_call",
        })

    if not tool_calls:
        _log.warning("[ClaudeCode] No se pudieron extraer tool_calls válidas, fallback a texto")
        return AIMessage(content=text)

    _log.info("[ClaudeCode] Parseadas %d tool_calls: %s",
              len(tool_calls), [tc["name"] for tc in tool_calls])
    return AIMessage(content="", tool_calls=tool_calls)


# ---------------------------------------------------------------------------
# Message conversion
# ---------------------------------------------------------------------------

def _messages_to_prompt(messages: List[BaseMessage], tool_system: str = "") -> str:
    parts = []
    if tool_system:
        parts.append(f"[System]: {tool_system}")

    has_tool_results = False
    for msg in messages:
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        if msg.type == "system":
            parts.append(f"[System]: {content}")
        elif msg.type == "human":
            parts.append(f"[User]: {content}")
        elif msg.type == "ai":
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                calls_str = json.dumps(
                    [{"name": tc["name"], "args": tc["args"]} for tc in msg.tool_calls],
                    ensure_ascii=False,
                )
                parts.append(f"[You previously called these tools]: {calls_str}")
            elif content:
                parts.append(f"[Assistant]: {content}")
        elif msg.type == "tool":
            has_tool_results = True
            tool_name = getattr(msg, "name", "unknown")
            parts.append(f"[Tool Result — {tool_name}]: {content}")
        else:
            parts.append(content)

    # Tras recibir resultados de tools, instruir a Claude sobre qué hacer ahora
    if has_tool_results and tool_system:
        parts.append(
            "[System]: The tool results are above. Now you MUST either:\n"
            "- Call another tool if you need more information (use the <<<TOOL_CALL>>> format)\n"
            "- Respond with a final text answer to the user summarizing what was done\n"
            "Do NOT repeat a tool call that already succeeded."
        )

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# ChatModel
# ---------------------------------------------------------------------------

class ClaudeCodeChatModel(BaseChatModel):
    """LangChain ChatModel con warm process pool por tenant via Claude Code CLI."""

    model_name: str = "claude-code-cli"
    timeout: int = TIMEOUT
    pool_key: str = "default"
    _bound_tools: list = []

    model_config = ConfigDict(underscore_attrs_are_private=True)

    def __init__(self, **kwargs):
        bound = kwargs.pop("_bound_tools", [])
        super().__init__(**kwargs)
        self._bound_tools = bound

    @property
    def _llm_type(self) -> str:
        return "claude-code-cli"

    def _get_tool_system(self) -> str:
        if not self._bound_tools:
            return ""
        return _build_tool_system_prompt(self._bound_tools)

    def _process_response(self, text: str) -> ChatResult:
        if self._bound_tools:
            msg = _parse_tool_response(text)
            # Log para debugging: si tenía tools pero no parseó ninguna
            if not msg.tool_calls and self._bound_tools:
                # Verificar si Claude estaba intentando llamar una tool pero con formato incorrecto
                tool_names = {t.name for t in self._bound_tools}
                mentioned = [n for n in tool_names if n in text]
                if mentioned:
                    _log.warning(
                        "[ClaudeCode] Claude mencionó tools %s en texto pero no usó el formato correcto. "
                        "Respuesta (primeros 200 chars): %s",
                        mentioned, text[:200],
                    )
        else:
            msg = AIMessage(content=text)
        return ChatResult(generations=[ChatGeneration(message=msg)])

    # ── sync ─────────────────────────────────────────────────────────────────
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        import subprocess
        prompt = _messages_to_prompt(messages, self._get_tool_system())
        try:
            result = subprocess.run(
                [_resolve_claude_bin(), "-p", "--dangerously-skip-permissions"],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding="utf-8",
                env=_clean_env(),
                cwd=_neutral_cwd(),
            )
            text = result.stdout.strip() or result.stderr.strip() or "Sin respuesta del CLI"
        except subprocess.TimeoutExpired:
            text = "Error: Claude Code CLI no respondió en el tiempo límite."
        except FileNotFoundError:
            text = "Error: Claude Code CLI no encontrado. Verifica que 'claude' esté en el PATH."
        except Exception as e:
            text = f"Error inesperado en Claude Code CLI: {e}"
        return self._process_response(text)

    # ── async ─────────────────────────────────────────────────────────────────
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        prompt = _messages_to_prompt(messages, self._get_tool_system())
        try:
            proc = await _acquire_process(self.pool_key)
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=prompt.encode("utf-8")),
                timeout=self.timeout,
            )
            text = stdout.decode("utf-8", errors="replace").strip()
            if not text:
                text = stderr.decode("utf-8", errors="replace").strip() or "Sin respuesta del CLI"
        except asyncio.TimeoutError:
            text = "Error: Claude Code CLI no respondió en el tiempo límite."
        except FileNotFoundError:
            text = "Error: Claude Code CLI no encontrado. Verifica que 'claude' esté en el PATH."
        except Exception as e:
            text = f"Error inesperado en Claude Code CLI: {e}"
        _log.info("[ClaudeCode] _agenerate key='%s': %d chars", self.pool_key, len(text))
        return self._process_response(text)

    # ── tool binding ─────────────────────────────────────────────────────────
    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        """Devuelve un clon con las tools almacenadas para prompt-based tool calling."""
        return ClaudeCodeChatModel(
            model_name=self.model_name,
            timeout=self.timeout,
            pool_key=self.pool_key,
            _bound_tools=list(tools),
        )

    # ── structured output ─────────────────────────────────────────────────────
    def with_structured_output(self, schema, *, method="json_mode", include_raw=False, **kwargs):
        def _build_json_instruction():
            if hasattr(schema, "model_json_schema"):
                schema_str = json.dumps(schema.model_json_schema(), ensure_ascii=False)
            elif hasattr(schema, "schema"):
                schema_str = json.dumps(schema.schema(), ensure_ascii=False)
            else:
                schema_str = str(schema)
            return (
                f"\n\nResponde ÚNICAMENTE con un objeto JSON válido que cumpla este esquema "
                f"(sin markdown, sin texto adicional):\n{schema_str}"
            )

        def _parse(raw_text: str):
            clean = re.sub(r"```(?:json)?\s*", "", raw_text)
            clean = re.sub(r"```", "", clean).strip()
            match = re.search(r"\{.*\}", clean, re.DOTALL)
            if match:
                clean = match.group(0)
            parsed = json.loads(clean)
            if hasattr(schema, "model_validate"):
                return schema.model_validate(parsed)
            return parsed

        def _invoke_and_parse(messages_input):
            if isinstance(messages_input, str):
                msgs = [HumanMessage(content=messages_input)]
            elif isinstance(messages_input, list):
                msgs = messages_input
            else:
                msgs = [messages_input]
            msgs = msgs + [HumanMessage(content=_build_json_instruction())]
            result = self._generate(msgs)
            return _parse(result.generations[0].message.content)

        async def _ainvoke_and_parse(messages_input):
            if isinstance(messages_input, str):
                msgs = [HumanMessage(content=messages_input)]
            elif isinstance(messages_input, list):
                msgs = messages_input
            else:
                msgs = [messages_input]
            msgs = msgs + [HumanMessage(content=_build_json_instruction())]
            result = await self._agenerate(msgs)
            return _parse(result.generations[0].message.content)

        return RunnableLambda(_invoke_and_parse, afunc=_ainvoke_and_parse)

    @property
    def _identifying_params(self) -> dict:
        return {"model_name": self.model_name, "pool_key": self.pool_key}
