import json
import logging
import re
from typing import Any, List, Optional
from uuid import uuid4

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from app.core.config import settings


class MockChatModel(BaseChatModel):
    """
    LLM simulado que responde de forma inteligente sin llamadas a API externas.
    Detecta el contexto del mensaje (agente, herramientas disponibles) y genera
    respuestas apropiadas para cada tipo de agente del sistema.
    """

    @property
    def _llm_type(self) -> str:
        return "mock"

    def bind_tools(self, tools, **kwargs):
        """Convierte herramientas a formato OpenAI y las enlaza como kwargs."""
        try:
            from langchain_core.utils.function_calling import convert_to_openai_tool
            formatted = [convert_to_openai_tool(t) for t in tools]
        except Exception:
            formatted = list(tools)
        return self.bind(tools=formatted, **kwargs)

    def with_structured_output(self, schema, method: str = "json_mode", **kwargs):
        """
        Devuelve un Runnable que, al invocarse, genera una respuesta JSON
        y la instancia como el schema Pydantic dado.
        """
        from langchain_core.runnables import RunnableLambda

        def _invoke(input_msg):
            # input_msg puede ser str o list de mensajes
            from langchain_core.messages import HumanMessage as HM
            if isinstance(input_msg, str):
                msgs = [HM(content=input_msg)]
            elif isinstance(input_msg, list):
                msgs = input_msg
            else:
                msgs = [HM(content=str(input_msg))]

            result = self._generate(msgs)
            content = result.generations[0].message.content

            # Parsear JSON
            try:
                data = json.loads(content)
            except Exception:
                # extraer primer bloque JSON del texto
                match = re.search(r'\{.*\}', content, re.DOTALL)
                data = json.loads(match.group(0)) if match else {}

            # Si schema es Pydantic model → instanciar
            try:
                return schema(**data)
            except Exception:
                return data

        return RunnableLambda(_invoke)

    def _generate(self, messages: List[BaseMessage], stop=None, run_manager=None, **kwargs) -> ChatResult:
        ai_msg = self._build_response(messages, kwargs)
        return ChatResult(generations=[ChatGeneration(message=ai_msg)])

    async def _agenerate(self, messages: List[BaseMessage], stop=None, run_manager=None, **kwargs) -> ChatResult:
        return self._generate(messages, stop, run_manager, **kwargs)

    def _build_response(self, messages: List[BaseMessage], kwargs: dict) -> AIMessage:
        full_text = " ".join(
            m.content if isinstance(m.content, str) else ""
            for m in messages
        ).lower()
        tools = kwargs.get("tools", [])

        # Si hay ToolMessage → herramienta ejecutada → respuesta final
        for m in reversed(messages):
            if isinstance(m, ToolMessage):
                snippet = m.content[:400] if isinstance(m.content, str) else str(m.content)[:400]
                return AIMessage(content=f"Tarea completada correctamente. Resultado: {snippet}")

        # Modo tool-calling: el agente debe elegir una herramienta
        if tools:
            return self._tool_call_response(full_text, tools, messages)

        # ── Coordinador: plan multi-agente ────────────────────────────────────
        if "coordinador general" in full_text or ("steps" in full_text and "agent" in full_text and "instruction" in full_text):
            return AIMessage(content=self._multi_agent_plan(full_text))

        # ── Orchestrator: clasificar dominio ──────────────────────────────────
        if ("billing|documents|compliance" in full_text
                or ("clasificador" in full_text and "billing" in full_text)
                or ("dominio" in full_text and "agente" in full_text)):
            return AIMessage(content=self._classify_domain(full_text))

        # ── Billing: extracción de datos ──────────────────────────────────────
        if ("client_name" in full_text and "amount_base" in full_text) or \
           ("extracción de datos de facturación" in full_text):
            return AIMessage(content=self._billing_json(full_text))

        # ── Compliance: alertas fiscales ──────────────────────────────────────
        if '"alertas"' in full_text or "vencimientos fiscales" in full_text:
            return AIMessage(content=json.dumps({
                "alertas": [
                    "El Modelo 303 (IVA) del T1 vence el 20 de abril de 2026.",
                    "El Modelo 111 (Retenciones IRPF) del T1 vence el 20 de abril de 2026.",
                    "El Modelo 200 (IS) anual vence el 25 de julio de 2026."
                ]
            }))

        # ── Compliance: resumen BOE ───────────────────────────────────────────
        if "resumen_boe" in full_text or "novedades del boe" in full_text:
            return AIMessage(content=json.dumps({
                "resumen_boe": "Sin novedades legislativas urgentes esta semana.",
                "boe_novedades": [
                    {"titulo": "Real Decreto 123/2026", "descripcion": "Modificación tipo IVA servicios digitales", "url": "#"}
                ]
            }))

        # ── Compliance: consulta fiscal ───────────────────────────────────────
        if "respuesta_consulta" in full_text or "asesor fiscal experto" in full_text:
            return AIMessage(content=json.dumps({
                "respuesta_consulta": (
                    "Basándome en la normativa fiscal española vigente, "
                    "la deducibilidad depende de que el gasto esté correlacionado con la actividad económica "
                    "y debidamente documentado con factura. Consulte con su gestor para casos específicos."
                )
            }))

        # ── Fallback genérico ─────────────────────────────────────────────────
        return AIMessage(content=json.dumps({"status": "ok", "message": "Respuesta simulada (MockLLM)"}))

    def _multi_agent_plan(self, text: str) -> str:
        """Genera un plan multi-agente en formato JSON para el coordinador."""
        steps = []
        if "nómin" in text or "nomina" in text or "emplead" in text:
            steps.append({"agent": "hr", "action": "generate_payrolls", "instruction": "Genera las nóminas en borrador para todos los empleados del mes actual."})
        if "factura" in text or "cobro" in text or "venta" in text:
            steps.append({"agent": "billing", "action": "list_invoices", "instruction": "Lista las facturas pendientes de cobro y genera un resumen."})
        if "fiscal" in text or "vencimiento" in text or "impuesto" in text or "trimestre" in text:
            steps.append({"agent": "compliance", "action": "check_alerts", "instruction": "Revisa los vencimientos fiscales del trimestre actual y genera alertas."})
        if not steps:
            steps.append({"agent": "billing", "action": "process", "instruction": "Procesa la solicitud del usuario."})
        return json.dumps({"steps": steps})

    def _classify_domain(self, text: str) -> str:
        """Devuelve una sola palabra: el dominio del agente a invocar."""
        mapping = {
            "nómina": "hr", "nomina": "hr", "empleado": "hr", "sueldo": "hr",
            "factura": "billing", "cobro": "billing", "venta": "billing", "cliente": "billing",
            "crm": "crm", "oportunidad": "crm", "lead": "crm", "comercial": "crm",
            "compliance": "compliance", "fiscal": "compliance", "iva": "compliance", "impuesto": "compliance",
            "documento": "documents", "escanear": "documents", "archivo": "documents",
            "correo": "email", "email": "email",
            "excel": "excel", "hoja de cálculo": "excel",
            "banco": "banking", "saldo": "banking", "transacción": "banking",
        }
        for kw, domain in mapping.items():
            if kw in text:
                return domain
        return "billing"

    def _billing_json(self, text: str) -> str:
        """Extrae o genera JSON de facturación simulado."""
        # Detectar si es una consulta/listado vs creación
        query_keywords = ["lista", "listar", "listado", "pendiente", "cobro", "consulta", "resumen", "ver", "mostrar", "cuántas", "cuantas"]
        is_query = any(kw in text for kw in query_keywords)
        if is_query:
            return json.dumps({
                "client_name": None,
                "client_nif": None,
                "invoice_number": None,
                "date": None,
                "due_date": None,
                "items": [],
                "amount_base": None,
                "tax_amount": None,
                "amount_total": None,
                "currency": "EUR",
                "notes": None,
                "is_query": True,
                "confidence": 0.9
            })
        return json.dumps({
            "client_name": "Cliente Demo S.L.",
            "client_nif": "B12345678",
            "invoice_number": f"MOCK-{uuid4().hex[:6].upper()}",
            "date": "2026-03-10",
            "due_date": "2026-04-10",
            "items": [
                {"description": "Servicio de consultoría", "quantity": "1", "unit_price": "1500.00", "tax_rate": "21"}
            ],
            "amount_base": "1500.00",
            "tax_amount": "315.00",
            "amount_total": "1815.00",
            "currency": "EUR",
            "notes": "Factura generada por Mock LLM para pruebas",
            "is_query": False,
            "confidence": 0.95
        })

    def _tool_call_response(self, full: str, tools: list, messages: List[BaseMessage]) -> AIMessage:
        """Genera una llamada a herramienta apropiada según el contexto."""
        tenant_id = self._extract_tenant_id(messages)

        # Obtener nombres de herramientas disponibles
        tool_names = []
        for t in tools:
            if isinstance(t, dict):
                tool_names.append(t.get("function", {}).get("name", ""))
            elif hasattr(t, "name"):
                tool_names.append(t.name)

        call_id = f"call_{uuid4().hex[:8]}"

        # ── HR: nóminas ───────────────────────────────────────────────────────
        if any("payroll" in n or "nomina" in n for n in tool_names):
            if "generate_all_payrolls" in tool_names and ("todos" in full or "all" in full or "nóminas" in full):
                return AIMessage(content="", tool_calls=[{
                    "id": call_id, "name": "generate_all_payrolls", "type": "tool_call",
                    "args": {"tenant_id": tenant_id, "month": 3, "year": 2026}
                }])
            if "list_employees" in tool_names:
                return AIMessage(content="", tool_calls=[{
                    "id": call_id, "name": "list_employees", "type": "tool_call",
                    "args": {"tenant_id": tenant_id}
                }])

        # ── CRM: oportunidades ────────────────────────────────────────────────
        if any("opportunit" in n or "oportunidad" in n or "leads" in n for n in tool_names):
            if "qualify_leads" in tool_names and ("cualif" in full or "leads" in full or "analiz" in full):
                return AIMessage(content="", tool_calls=[{
                    "id": call_id, "name": "qualify_leads", "type": "tool_call",
                    "args": {"tenant_id": tenant_id}
                }])
            if "list_opportunities" in tool_names:
                return AIMessage(content="", tool_calls=[{
                    "id": call_id, "name": "list_opportunities", "type": "tool_call",
                    "args": {"tenant_id": tenant_id, "stage": "all"}
                }])

        # ── Documentos ────────────────────────────────────────────────────────
        if "list_tenant_documents" in tool_names:
            return AIMessage(content="", tool_calls=[{
                "id": call_id, "name": "list_tenant_documents", "type": "tool_call",
                "args": {"tenant_id": tenant_id}
            }])

        # ── Fallback: respuesta directa sin tool ──────────────────────────────
        return AIMessage(content="He procesado tu solicitud. Todo está en orden (respuesta simulada).")

    def _extract_tenant_id(self, messages: List[BaseMessage]) -> str:
        """Extrae el tenant_id del contexto de los mensajes."""
        uuid_pattern = re.compile(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            re.IGNORECASE
        )
        for m in reversed(messages):
            if isinstance(m.content, str):
                match = uuid_pattern.search(m.content)
                if match:
                    return match.group(0)
        return "00000000-0000-0000-0000-000000000000"


def _get_ollama_fallback(temperature: float = 0) -> BaseChatModel:
    """Fallback local siempre disponible."""
    return ChatOllama(
        model="mistral-nemo",
        base_url=settings.OLLAMA_BASE_URL,
        temperature=temperature,
    )


def get_llm(
    temperature: float = 0,
    format_output: str = None,
    provider: str = None
) -> BaseChatModel:
    """
    Fábrica centralizada para instanciar el modelo LLM configurado.
    Soporta: groq, gemini, openai, anthropic, ollama.
    Si el proveedor principal falla por cuota/credenciales o error en tiempo de ejecución, usa Ollama como fallback.
    """
    selected_provider = provider or settings.DEFAULT_LLM_PROVIDER.lower()
    fallback = _get_ollama_fallback(temperature)

    if selected_provider == "groq":
        try:
            from langchain_groq import ChatGroq
            if not settings.GROQ_API_KEY:
                return fallback
            
            # Usamos llama-3.1-8b-instant si el 70b está saturado o para mayor velocidad
            # Pero por defecto mantenemos el configurado con fallback automático
            kwargs = {
                "model": settings.GROQ_MODEL or "llama-3.3-70b-versatile",
                "api_key": settings.GROQ_API_KEY,
                "temperature": temperature,
                "max_tokens": 20000,
                "timeout": 30,
            }
            if format_output == "json":
                kwargs["response_format"] = {"type": "json_object"}
            base_llm = ChatGroq(**kwargs)
            return base_llm.with_fallbacks([fallback])
        except Exception as e:
            logging.getLogger(__name__).warning("Error iniciando Groq (%s), usando Ollama.", e)
            return fallback

    elif selected_provider == "gemini":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            if not settings.GEMINI_API_KEY:
                return fallback
            base_llm = ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL or "gemini-2.5-flash-preview-04-17",
                google_api_key=settings.GEMINI_API_KEY,
                temperature=temperature,
                max_output_tokens=20000,
                timeout=30,
            )
            return base_llm.with_fallbacks([fallback])
        except Exception as e:
            logging.getLogger(__name__).warning("Error iniciando Gemini (%s), usando Ollama.", e)
            return fallback

    elif selected_provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
            if not settings.ANTHROPIC_API_KEY:
                return fallback
            base_llm = ChatAnthropic(
                model_name="claude-3-5-sonnet-20240620",
                temperature=temperature,
                api_key=settings.ANTHROPIC_API_KEY,
                max_tokens=4096,
                timeout=30,
            )
            return base_llm.with_fallbacks([fallback])
        except Exception as e:
            logging.getLogger(__name__).warning("Error iniciando Anthropic (%s), usando Ollama.", e)
            return fallback

    elif selected_provider == "openai":
        try:
            if not settings.OPENAI_API_KEY:
                return fallback
            kwargs = {
                "model_name": settings.OPENAI_MODEL or "gpt-4o",
                "temperature": temperature,
                "api_key": settings.OPENAI_API_KEY,
                "max_tokens": 20000,
                "timeout": 30,
            }
            if format_output == "json":
                kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}
            base_llm = ChatOpenAI(**kwargs)
            return base_llm.with_fallbacks([fallback])
        except Exception as e:
            logging.getLogger(__name__).warning("Error iniciando OpenAI (%s), usando Ollama.", e)
            return fallback

    elif selected_provider == "openrouter":
        try:
            if not settings.OPENROUTER_API_KEY:
                return fallback
                
            models = [
                "qwen/qwen3-235b-a22b-thinking-2507", # Qwen 3 235B
                "google/gemma-3-27b-it:free", # Gemma 3 27B
                "mistralai/mistral-small-3.1-24b-instruct:free", # Mistral Small 3.1 24B
                "google/gemini-2.0-flash-exp:free" # Gemini 2.0 Flash Exp
            ]
            
            # Si el usuario especificó uno en .env, lo ponemos el primero (si no está ya)
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
                    # Limitamos tokens para evitar el error 402 de reserva de saldo en cuentas gratuitas
                    "max_tokens": 8000,
                    # Desactivar retries de Langchain para que pase al siguiente fallback inmediatamente si OpenRouter está rate-limited
                    "max_retries": 0,
                }
                if format_output == "json":
                    kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}
                chat_models.append(ChatOpenAI(**kwargs))
            
            # Encadenar con fallbacks: si el primero falla (ej. saturación), salta al segundo, etc.
            primary_llm = chat_models[0]
            if len(chat_models) > 1:
                return primary_llm.with_fallbacks(chat_models[1:])
            return primary_llm
            
        except Exception as e:
            logging.getLogger(__name__).warning("Error iniciando OpenRouter (%s).", e)
            raise e

    elif selected_provider == "mock":
        return MockChatModel()

    else:
        # Ollama (local)
        kwargs = {
            "model": "mistral-nemo",
            "base_url": settings.OLLAMA_BASE_URL,
            "temperature": temperature,
        }
        if format_output:
            kwargs["format"] = format_output
        return ChatOllama(**kwargs)


def get_llm_with_fallback(
    temperature: float = 0,
    provider: str = None
) -> BaseChatModel:
    """Mantenido por compatibilidad, get_llm ya incluye fallbacks."""
    return get_llm(temperature=temperature, provider=provider)
