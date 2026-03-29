"""
Fábrica centralizada de LLMs.

Soporta: groq, gemini, openai, anthropic, openrouter, mock.
Incluye fallback chains automáticas y configuración per-tenant desde BD.

Módulos internos:
  _llm_mock.py   — MockChatModel (testing sin API keys)
  _llm_gemini.py — Sanitizer de mensajes + wrapper para Gemini
"""
import logging
from contextvars import ContextVar
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core._llm_mock import MockChatModel
from app.core._llm_gemini import GeminiSafeWrapper

# ContextVar para propagar el LLM del tenant a todos los agentes del mismo request
_tenant_llm_ctx: ContextVar = ContextVar("_tenant_llm_ctx", default=None)


def set_tenant_llm_context(llm) -> None:
    """Almacena el LLM resuelto del tenant en el contexto async actual."""
    _tenant_llm_ctx.set(llm)


def get_llm(
    temperature: float = 0,
    format_output: str = None,
    provider: str = None,
    max_tokens: int | None = None,
) -> BaseChatModel:
    """
    Fábrica centralizada para instanciar el modelo LLM configurado.
    Soporta: groq, gemini, openai, anthropic, openrouter.
    Fallback final: MockChatModel (solo en testing) o lanza error en producción.
    """
    # Si hay un LLM de tenant precargado (vía set_tenant_llm_context) y no se fuerza un provider,
    # usarlo directamente para respetar la configuración del usuario en la UI.
    if provider is None and format_output != "json":
        ctx_llm = _tenant_llm_ctx.get()
        if ctx_llm is not None:
            return ctx_llm

    selected_provider = provider or settings.DEFAULT_LLM_PROVIDER.lower()
    mock_fallback = MockChatModel()

    base_fallbacks: list[BaseChatModel] = [mock_fallback] if settings.ENVIRONMENT == "testing" else []

    # En testing sin API key → ir directo al mock
    if settings.ENVIRONMENT == "testing":
        has_key = (
            (selected_provider == "groq" and settings.GROQ_API_KEY) or
            (selected_provider == "gemini" and settings.GEMINI_API_KEY) or
            (selected_provider == "openai" and settings.OPENAI_API_KEY) or
            (selected_provider == "anthropic" and settings.ANTHROPIC_API_KEY) or
            (selected_provider == "openrouter" and settings.OPENROUTER_API_KEY)
        )
        if not has_key:
            return mock_fallback

    if selected_provider == "groq":
        return _build_groq(temperature, format_output, max_tokens, base_fallbacks, mock_fallback)

    elif selected_provider == "gemini":
        return _build_gemini(temperature, format_output, max_tokens, base_fallbacks, mock_fallback)

    elif selected_provider == "anthropic":
        return _build_anthropic(temperature, format_output, max_tokens, base_fallbacks, mock_fallback)

    elif selected_provider == "openai":
        return _build_openai(temperature, format_output, max_tokens, base_fallbacks, mock_fallback)

    elif selected_provider == "openrouter":
        return _build_openrouter(temperature, format_output, max_tokens, base_fallbacks)

    elif selected_provider == "mock":
        return MockChatModel()

    else:
        logging.getLogger(__name__).warning(
            "Proveedor LLM desconocido: '%s'. Usando mock.", selected_provider
        )
        return mock_fallback


def get_llm_with_fallback(
    temperature: float = 0,
    provider: str = None
) -> BaseChatModel:
    """Mantenido por compatibilidad, get_llm ya incluye fallbacks."""
    return get_llm(temperature=temperature, provider=provider)


async def get_llm_for_tenant(
    tenant_id,
    db,
    temperature: float = 0,
    format_output: str = None,
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

            if not pdata.get("enabled"):
                _log.warning("Proveedor LLM '%s' está desactivado para el tenant %s", provider, tenant_id)
                raise ValueError(
                    f"El proveedor de IA '{provider}' está desactivado. "
                    "Actívalo en Configuración → API Keys."
                )
            if not pdata.get("api_key"):
                _log.warning("Proveedor LLM '%s' sin API key para el tenant %s", provider, tenant_id)
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
            elif provider == "gemini":
                from langchain_google_genai import ChatGoogleGenerativeAI
                return GeminiSafeWrapper(ChatGoogleGenerativeAI(
                    model=model or settings.GEMINI_MODEL or "gemini-2.5-flash",
                    google_api_key=api_key,
                    temperature=temperature,
                    max_output_tokens=20000,
                    timeout=30,
                ))
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
    except Exception as e:
        _log.warning("Error leyendo LLM config del tenant (%s), usando config global.", e)

    return get_llm(temperature=temperature, format_output=format_output)


def get_embedder():
    """
    Devuelve el modelo de embeddings según EMBEDDINGS_PROVIDER en config.

    Opciones:
      - local   → HuggingFace BAAI/bge-m3 (offline, sin coste, estado del arte multilingüe)
      - gemini  → models/text-embedding-004  (requiere GEMINI_API_KEY)
      - openai  → text-embedding-3-small     (requiere OPENAI_API_KEY)

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
        except Exception as e:
            _log.warning("HuggingFaceEmbeddings no disponible: %s", e)

    elif provider == "gemini":
        if settings.GEMINI_API_KEY:
            try:
                from langchain_google_genai import GoogleGenerativeAIEmbeddings
                return GoogleGenerativeAIEmbeddings(
                    model="models/text-embedding-004",
                    google_api_key=settings.GEMINI_API_KEY,
                )
            except Exception as e:
                _log.warning("GoogleGenerativeAIEmbeddings no disponible: %s", e)
        else:
            _log.warning("EMBEDDINGS_PROVIDER=gemini pero GEMINI_API_KEY está vacía.")

    elif provider == "openai":
        if settings.OPENAI_API_KEY:
            try:
                from langchain_openai import OpenAIEmbeddings
                return OpenAIEmbeddings(
                    model="text-embedding-3-small",
                    api_key=settings.OPENAI_API_KEY,
                )
            except Exception as e:
                _log.warning("OpenAIEmbeddings no disponible: %s", e)
        else:
            _log.warning("EMBEDDINGS_PROVIDER=openai pero OPENAI_API_KEY está vacía.")

    _log.warning("No hay proveedor de embeddings disponible. Las funciones RAG estarán desactivadas.")
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

        groq_fallbacks = list(base_fallbacks)
        if settings.OPENAI_API_KEY:
            try:
                openai_kwargs = {
                    "model_name": settings.OPENAI_MODEL or "gpt-4o-mini",
                    "temperature": temperature,
                    "api_key": settings.OPENAI_API_KEY,
                    "max_tokens": 4096,
                    "timeout": 30,
                }
                if format_output == "json":
                    openai_kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}
                groq_fallbacks.insert(0, ChatOpenAI(**openai_kwargs))
            except Exception:
                logging.getLogger(__name__).warning("Failed to init OpenAI fallback for Groq", exc_info=True)
        return base_llm.with_fallbacks(groq_fallbacks)
    except Exception as e:
        logging.getLogger(__name__).warning("Error iniciando Groq (%s), usando fallbacks.", e)
        return mock_fallback


def _build_gemini(temperature, format_output, max_tokens, base_fallbacks, mock_fallback):
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        if not settings.GEMINI_API_KEY:
            return mock_fallback
        base_llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL or "gemini-2.5-flash",
            google_api_key=settings.GEMINI_API_KEY,
            temperature=temperature,
            max_output_tokens=max_tokens or 20000,
            timeout=30,
        )
        fallback_chain = list(base_fallbacks)
        try:
            from langchain_groq import ChatGroq
            if settings.GROQ_API_KEY:
                groq_fallback = ChatGroq(
                    model=settings.GROQ_MODEL or "llama-3.3-70b-versatile",
                    api_key=settings.GROQ_API_KEY,
                    temperature=temperature,
                    max_tokens=20000,
                    timeout=30,
                )
                fallback_chain.insert(0, groq_fallback)
        except Exception:
            logging.getLogger(__name__).warning("Failed to init Groq fallback for Gemini", exc_info=True)
        return GeminiSafeWrapper(base_llm.with_fallbacks(fallback_chain))
    except Exception as e:
        logging.getLogger(__name__).warning("Error iniciando Gemini (%s), usando fallbacks.", e)
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
        anthropic_fallbacks = list(base_fallbacks)
        if settings.GEMINI_API_KEY:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                anthropic_fallbacks.insert(0, ChatGoogleGenerativeAI(
                    model=settings.GEMINI_MODEL or "gemini-2.5-flash",
                    google_api_key=settings.GEMINI_API_KEY,
                    temperature=temperature,
                    max_output_tokens=4096,
                    timeout=30,
                ))
            except Exception:
                logging.getLogger(__name__).warning("Failed to init Gemini fallback for Anthropic", exc_info=True)
        if settings.OPENAI_API_KEY:
            try:
                anthropic_fallbacks.insert(
                    1 if settings.GEMINI_API_KEY else 0,
                    ChatOpenAI(
                        model_name=settings.OPENAI_MODEL or "gpt-4o-mini",
                        temperature=temperature,
                        api_key=settings.OPENAI_API_KEY,
                        max_tokens=4096,
                        timeout=30,
                    )
                )
            except Exception:
                logging.getLogger(__name__).warning("Failed to init OpenAI fallback for Anthropic", exc_info=True)
        return base_llm.with_fallbacks(anthropic_fallbacks)
    except Exception as e:
        logging.getLogger(__name__).warning("Error iniciando Anthropic (%s), usando fallbacks.", e)
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
    except Exception as e:
        logging.getLogger(__name__).warning("Error iniciando OpenAI (%s), usando fallbacks.", e)
        return mock_fallback


def _build_openrouter(temperature, format_output, max_tokens, base_fallbacks):
    try:
        if not settings.OPENROUTER_API_KEY:
            return MockChatModel()

        models = [
            "qwen/qwen3-235b-a22b-thinking-2507",
            "google/gemma-3-27b-it:free",
            "mistralai/mistral-small-3.1-24b-instruct:free",
            "google/gemini-2.0-flash-exp:free"
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

    except Exception as e:
        logging.getLogger(__name__).warning("Error iniciando OpenRouter (%s).", e)
        raise e
