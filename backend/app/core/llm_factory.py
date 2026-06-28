"""
Fábrica centralizada de LLMs.

Soporta: groq, openai, anthropic, openrouter, claude_code, mock.
Incluye fallback chains automáticas y configuración per-tenant desde BD.

Módulos internos:
  _llm_mock.py — MockChatModel (testing sin API keys)
"""

import logging
from contextvars import ContextVar
from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.llm.claude_code import ClaudeCodeChatModel
from app.core.llm.mock import MockChatModel
from app.core.llm_trace import attach_to as _attach_trace

_log = logging.getLogger(__name__)

# ContextVar para propagar el LLM del tenant a todos los agentes del mismo request
_tenant_llm_ctx: ContextVar = ContextVar("_tenant_llm_ctx", default=None)


@lru_cache(maxsize=1)
def _mock_fallback() -> MockChatModel:
    """Singleton perezoso del LLM simulado.

    MockChatModel no tiene estado mutable por instancia, así que reutilizar una
    única instancia evita asignarla en cada llamada a get_llm() (28 callers) — la
    asignación previa era trabajo muerto en el camino caliente de producción.
    """
    return MockChatModel()


def set_tenant_llm_context(llm, provider: str | None = None) -> None:
    """Almacena el LLM resuelto del tenant (y su provider) en el contexto async actual.

    `provider` se declara explícitamente en construcción para que la identidad
    del proveedor no dependa de introspeccionar `type(llm).__module__` (un
    detalle interno de LangChain que cambia entre versiones). Si se omite, se
    cae a la introspección legacy por compatibilidad.
    """
    _tenant_llm_ctx.set((llm, provider))


def _resolve_active_provider() -> str:
    """Determina el provider LLM activo: ContextVar del tenant o config global."""
    ctx = _tenant_llm_ctx.get()
    if ctx is not None:
        ctx_llm, provider_tag = ctx
        if provider_tag:
            return provider_tag.lower()
        # Fallback legacy: deducir por el módulo de la clase del LLM
        module = getattr(type(ctx_llm), "__module__", "") or ""
        if "anthropic" in module.lower():
            return "anthropic"
        return "other"
    return (settings.DEFAULT_LLM_PROVIDER or "openai").lower()


def make_cached_system_message(text: str):
    """
    Crea un SystemMessage que activa el prompt caching de Anthropic cuando el
    provider activo es 'anthropic'. Para cualquier otro provider devuelve un
    SystemMessage estándar sin overhead.

    Uso en agentes:
        sys_msg = make_cached_system_message(SYSTEM_PROMPT)
    """
    from langchain_core.messages import SystemMessage

    if _resolve_active_provider() == "anthropic":
        return SystemMessage(content=[{
            "type": "text",
            "text": text,
            "cache_control": {"type": "ephemeral"},
        }])
    return SystemMessage(content=text)


def get_llm(
    temperature: float = 0,
    format_output: str | None = None,
    provider: str | None = None,
    max_tokens: int | None = None,
) -> BaseChatModel:
    """
    Fábrica centralizada para instanciar el modelo LLM configurado.
    Soporta: groq, openai, anthropic, openrouter, claude_code.
    Fallback final: MockChatModel (solo en testing) o lanza error en producción.
    """
    # Si hay un LLM de tenant precargado (vía set_tenant_llm_context) y no se fuerza un provider,
    # usarlo directamente para respetar la configuración del usuario en la UI.
    if provider is None:
        ctx = _tenant_llm_ctx.get()
        if ctx is not None:
            ctx_llm, _ = ctx
            return _attach_trace(ctx_llm)

    selected_provider = provider or settings.DEFAULT_LLM_PROVIDER.lower()
    mock_fallback = _mock_fallback()

    base_fallbacks: list[BaseChatModel] = (
        [mock_fallback] if settings.ENVIRONMENT == "testing" else []
    )

    # En testing sin API key → ir directo al mock
    if settings.ENVIRONMENT == "testing":
        has_key = (
            (selected_provider == "groq" and settings.GROQ_API_KEY)
            or (selected_provider == "openai" and settings.OPENAI_API_KEY)
            or (selected_provider == "anthropic" and settings.ANTHROPIC_API_KEY)
            or (selected_provider == "openrouter" and settings.OPENROUTER_API_KEY)
        )
        if not has_key:
            return _attach_trace(mock_fallback)

    if selected_provider == "groq":
        return _attach_trace(
            _build_groq(temperature, format_output, max_tokens, base_fallbacks, mock_fallback)
        )

    elif selected_provider == "anthropic":
        return _attach_trace(
            _build_anthropic(
                temperature, format_output, max_tokens, base_fallbacks, mock_fallback
            )
        )

    elif selected_provider == "openai":
        return _attach_trace(
            _build_openai(temperature, format_output, max_tokens, base_fallbacks, mock_fallback)
        )

    elif selected_provider == "openrouter":
        return _attach_trace(
            _build_openrouter(temperature, format_output, max_tokens, base_fallbacks)
        )

    elif selected_provider == "claude_code":
        return _attach_trace(ClaudeCodeChatModel())

    elif selected_provider == "mock":
        return _attach_trace(_mock_fallback())

    else:
        logging.getLogger(__name__).warning(
            "Proveedor LLM desconocido: '%s'. Usando mock.", selected_provider
        )
        return _attach_trace(mock_fallback)


def get_llm_with_fallback(temperature: float = 0, provider: str | None = None) -> BaseChatModel:
    """Mantenido por compatibilidad, get_llm ya incluye fallbacks."""
    return get_llm(temperature=temperature, provider=provider)


async def get_llm_for_tenant(
    tenant_id,
    db,
    temperature: float = 0,
    format_output: str | None = None,
) -> BaseChatModel:
    """
    Devuelve el LLM configurado para el tenant específico.
    Si el tenant tiene config en BD (y el provider está enabled y tiene key),
    usa esa configuración. Si no, cae al get_llm() global con el .env.
    """
    _log = logging.getLogger(__name__)
    try:
        from sqlalchemy import select

        from app.db.models.models import TenantLlmConfig
        from app.services.encryption import decrypt_credentials

        result = await db.execute(
            select(TenantLlmConfig).where(TenantLlmConfig.tenant_id == tenant_id)
        )
        cfg = result.scalar_one_or_none()

        if cfg and cfg.encrypted_keys:
            keys = decrypt_credentials(cfg.encrypted_keys)
            provider = cfg.active_llm_provider
            pdata = keys.get(provider, {})

            # claude_code no necesita API key ni enabled — usa la sesión del CLI local
            if provider == "claude_code":
                _log.info("Usando Claude Code CLI para tenant %s", tenant_id)
                return ClaudeCodeChatModel(pool_key=str(tenant_id))

            if not pdata.get("enabled"):
                _log.warning(
                    "Proveedor LLM '%s' está desactivado para el tenant %s", provider, tenant_id
                )
                raise ValueError(
                    f"El proveedor de IA '{provider}' está desactivado. "
                    "Actívalo en Configuración → API Keys."
                )

            if not pdata.get("api_key"):
                _log.warning(
                    "Proveedor LLM '%s' sin API key para el tenant %s", provider, tenant_id
                )
                raise ValueError(
                    f"El proveedor de IA '{provider}' no tiene API Key configurada. "
                    "Añádela en Configuración → API Keys."
                )

            api_key = pdata["api_key"]
            model = pdata.get("model") or None
            _log.info("Usando LLM del tenant: provider=%s", provider)

            if provider == "anthropic":
                from langchain_anthropic import ChatAnthropic

                return ChatAnthropic(
                    model_name=model or settings.ANTHROPIC_MODEL or "claude-sonnet-4-6",
                    temperature=temperature,
                    api_key=api_key,
                    max_tokens=4096,
                    timeout=30,
                )
            elif provider == "openai":
                kwargs = {
                    "model_name": model or settings.OPENAI_MODEL or "gpt-4o-mini",
                    "temperature": temperature,
                    "api_key": api_key,
                    "max_tokens": 20000,
                    "timeout": 30,
                }
                if format_output == "json":
                    kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}
                return ChatOpenAI(**kwargs)
            elif provider == "groq":
                from langchain_groq import ChatGroq

                kwargs = {
                    "model": model or settings.GROQ_MODEL or "llama-3.3-70b-versatile",
                    "api_key": api_key,
                    "temperature": temperature,
                    "max_tokens": 20000,
                    "timeout": 30,
                }
                if format_output == "json":
                    kwargs["response_format"] = {"type": "json_object"}
                return ChatGroq(**kwargs)

    except ValueError:
        raise
    except (SQLAlchemyError, KeyError, ImportError) as e:
        _log.warning("Error leyendo LLM config del tenant (%s), usando config global.", e)

    return get_llm(temperature=temperature, format_output=format_output)


def get_embedder():
    """
    Devuelve el modelo de embeddings según EMBEDDINGS_PROVIDER en config.

    Opciones:
      - local   → HuggingFace BAAI/bge-m3 (offline, sin coste, estado del arte multilingüe)
      - openai  → text-embedding-3-small  (requiere OPENAI_API_KEY)

    Nota: Anthropic (Claude) y Groq no tienen API de embeddings propia.
    """
    _log = logging.getLogger(__name__)
    provider = (settings.EMBEDDINGS_PROVIDER or "local").lower()

    if provider == "local":
        try:
            from langchain_huggingface import HuggingFaceEmbeddings

            model_name = settings.EMBEDDINGS_LOCAL_MODEL or "BAAI/bge-m3"
            _log.info("Cargando embeddings locales: %s", model_name)
            return HuggingFaceEmbeddings(model_name=model_name)
        except (ImportError, OSError, ValueError) as e:
            _log.warning("HuggingFaceEmbeddings no disponible: %s", e)

    elif provider == "openai":
        if settings.OPENAI_API_KEY:
            try:
                from langchain_openai import OpenAIEmbeddings

                return OpenAIEmbeddings(
                    model="text-embedding-3-small",
                    api_key=settings.OPENAI_API_KEY,
                )
            except (ImportError, OSError, ValueError) as e:
                _log.warning("OpenAIEmbeddings no disponible: %s", e)
        else:
            _log.warning("EMBEDDINGS_PROVIDER=openai pero OPENAI_API_KEY está vacía.")

    _log.warning(
        "No hay proveedor de embeddings disponible. Las funciones RAG estarán desactivadas."
    )
    return None


# ---------------------------------------------------------------------------
# Helpers para construir fallbacks individuales
# ---------------------------------------------------------------------------


def _try_openai_fallback(
    temperature: float, format_output: str | None, max_tokens: int | None = None
) -> "ChatOpenAI | None":
    if not settings.OPENAI_API_KEY:
        return None
    try:
        kwargs = {
            "model_name": settings.OPENAI_MODEL or "gpt-4o-mini",
            "temperature": temperature,
            "api_key": settings.OPENAI_API_KEY,
            "max_tokens": max_tokens or 4096,
            "timeout": 30,
        }
        if format_output == "json":
            kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}
        return ChatOpenAI(**kwargs)
    except (ImportError, ValueError, TypeError) as exc:
        _log.warning("Failed to init OpenAI fallback: %s", exc)
        return None


def _try_groq_fallback(temperature: float, max_tokens: int | None = None) -> "BaseChatModel | None":
    if not settings.GROQ_API_KEY:
        return None
    try:
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=settings.GROQ_MODEL or "llama-3.3-70b-versatile",
            api_key=settings.GROQ_API_KEY,
            temperature=temperature,
            max_tokens=max_tokens or 20000,
            timeout=30,
        )
    except (ImportError, ValueError, TypeError) as exc:
        _log.warning("Failed to init Groq fallback: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Builders internos por provider (reducen la complejidad ciclomática de get_llm)
# ---------------------------------------------------------------------------


def _build_groq(temperature, format_output, max_tokens, base_fallbacks, mock_fallback):
    try:
        from langchain_groq import ChatGroq

        if not settings.GROQ_API_KEY:
            return mock_fallback
        kwargs = {
            "model": settings.GROQ_MODEL or "llama-3.3-70b-versatile",
            "api_key": settings.GROQ_API_KEY,
            "temperature": temperature,
            "max_tokens": max_tokens or 20000,
            "timeout": 30,
        }
        if format_output == "json":
            kwargs["response_format"] = {"type": "json_object"}
        base_llm = ChatGroq(**kwargs)
        fallbacks = list(base_fallbacks)
        openai_fb = _try_openai_fallback(temperature, format_output)
        if openai_fb:
            fallbacks.insert(0, openai_fb)
        return base_llm.with_fallbacks(fallbacks)
    except (ImportError, ValueError, TypeError) as e:
        _log.warning("Error iniciando Groq (%s), usando fallbacks.", e)
        return mock_fallback


def _build_anthropic(temperature, format_output, max_tokens, base_fallbacks, mock_fallback):
    try:
        from langchain_anthropic import ChatAnthropic

        if not settings.ANTHROPIC_API_KEY:
            return mock_fallback
        base_llm = ChatAnthropic(
            model_name=settings.ANTHROPIC_MODEL or "claude-sonnet-4-6",
            temperature=temperature,
            api_key=settings.ANTHROPIC_API_KEY,
            max_tokens=max_tokens or 4096,
            timeout=30,
        )
        fallbacks = list(base_fallbacks)
        openai_fb = _try_openai_fallback(temperature, format_output)
        if openai_fb:
            fallbacks.insert(0, openai_fb)
        return base_llm.with_fallbacks(fallbacks)
    except (ImportError, ValueError, TypeError) as e:
        _log.warning("Error iniciando Anthropic (%s), usando fallbacks.", e)
        return mock_fallback


def _build_openai(temperature, format_output, max_tokens, base_fallbacks, mock_fallback):
    try:
        if not settings.OPENAI_API_KEY:
            return mock_fallback
        kwargs = {
            "model_name": settings.OPENAI_MODEL or "gpt-4o-mini",
            "temperature": temperature,
            "api_key": settings.OPENAI_API_KEY,
            "max_tokens": max_tokens or 20000,
            "timeout": 30,
        }
        if format_output == "json":
            kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}
        base_llm = ChatOpenAI(**kwargs)
        return base_llm.with_fallbacks(base_fallbacks)
    except (ImportError, ValueError, TypeError) as e:
        _log.warning("Error iniciando OpenAI (%s), usando fallbacks.", e)
        return mock_fallback


def _build_openrouter(temperature, format_output, max_tokens, base_fallbacks):
    try:
        if not settings.OPENROUTER_API_KEY:
            return _mock_fallback()

        models = [
            "qwen/qwen3-235b-a22b-thinking-2507",
            "google/gemma-3-27b-it:free",
            "mistralai/mistral-small-3.1-24b-instruct:free",
        ]

        custom_model = settings.OPENROUTER_MODEL
        if custom_model and custom_model not in models:
            models.insert(0, custom_model)

        chat_models = []
        for m in models:
            kwargs = {
                "model_name": m,
                "temperature": temperature,
                "api_key": settings.OPENROUTER_API_KEY,
                "base_url": "https://openrouter.ai/api/v1",
                "max_tokens": max_tokens or 2000,
                "max_retries": 0,
            }
            if format_output == "json":
                kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}
            chat_models.append(ChatOpenAI(**kwargs))

        primary_llm = chat_models[0]
        rest_of_models = list(chat_models[1:]) + list(base_fallbacks)
        return primary_llm.with_fallbacks(rest_of_models)

    except (ImportError, ValueError, TypeError) as e:
        _log.warning("Error iniciando OpenRouter (%s).", e)
        raise
