"""
LLM simulado para testing y desarrollo sin API keys.
Detecta el contexto del mensaje y genera respuestas apropiadas para cada agente.
"""
import json
import re
from typing import List
from uuid import uuid4

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult


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
            from langchain_core.messages import HumanMessage as HM
            if isinstance(input_msg, str):
                msgs = [HM(content=input_msg)]
            elif isinstance(input_msg, list):
                msgs = input_msg
            else:
                msgs = [HM(content=str(input_msg))]

            result = self._generate(msgs)
            content = result.generations[0].message.content

            try:
                data = json.loads(content)
            except Exception:
                match = re.search(r'\{.*\}', content, re.DOTALL)
                data = json.loads(match.group(0)) if match else {}

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

        # ── Coordinador: plan multi-agente ──
        if "coordinador general" in full_text or ("steps" in full_text and "agent" in full_text and "instruction" in full_text):
            return AIMessage(content=self._multi_agent_plan(full_text))

        # ── Orchestrator: clasificar dominio ──
        if ("billing|documents|compliance" in full_text
                or ("clasificador" in full_text and "billing" in full_text)
                or ("dominio" in full_text and "agente" in full_text)):
            return AIMessage(content=self._classify_domain(full_text))

        # ── Billing: extracción de datos ──
        if ("client_name" in full_text and "amount_base" in full_text) or \
           ("extracción de datos de facturación" in full_text):
            return AIMessage(content=self._billing_json(full_text))

        # ── Compliance: alertas fiscales ──
        if '"alertas"' in full_text or "vencimientos fiscales" in full_text:
            return AIMessage(content=json.dumps({
                "alertas": [
                    "El Modelo 303 (IVA) del T1 vence el 20 de abril de 2026.",
                    "El Modelo 111 (Retenciones IRPF) del T1 vence el 20 de abril de 2026.",
                    "El Modelo 200 (IS) anual vence el 25 de julio de 2026."
                ]
            }))

        # ── Compliance: resumen BOE ──
        if "resumen_boe" in full_text or "novedades del boe" in full_text:
            return AIMessage(content=json.dumps({
                "resumen_boe": "Sin novedades legislativas urgentes esta semana.",
                "boe_novedades": [
                    {"titulo": "Real Decreto 123/2026", "descripcion": "Modificación tipo IVA servicios digitales", "url": "#"}
                ]
            }))

        # ── Compliance: consulta fiscal ──
        if "respuesta_consulta" in full_text or "asesor fiscal experto" in full_text:
            return AIMessage(content=json.dumps({
                "respuesta_consulta": (
                    "Basándome en la normativa fiscal española vigente, "
                    "la deducibilidad depende de que el gasto esté correlacionado con la actividad económica "
                    "y debidamente documentado con factura. Consulte con su gestor para casos específicos."
                )
            }))

        # ── Fallback genérico ──
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

        tool_names = []
        for t in tools:
            if isinstance(t, dict):
                tool_names.append(t.get("function", {}).get("name", ""))
            elif hasattr(t, "name"):
                tool_names.append(t.name)

        call_id = f"call_{uuid4().hex[:8]}"

        # ── HR: nóminas ──
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

        # ── CRM: oportunidades ──
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

        # ── Documentos ──
        if "list_tenant_documents" in tool_names:
            return AIMessage(content="", tool_calls=[{
                "id": call_id, "name": "list_tenant_documents", "type": "tool_call",
                "args": {"tenant_id": tenant_id}
            }])

        # ── Fallback: respuesta directa sin tool ──
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
