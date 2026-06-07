"""
Agente gestor de correos electrónicos.
Lee la bandeja de entrada y envía correos usando IMAP/SMTP real (con fallback a mock).
Si el tenant tiene credenciales de email configuradas → usa el servidor real.
Si no → usa datos de demostración para no romper el flujo.
"""

import logging
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agents.base import AgentState
from app.agents.types import StepResult
from app.core.llm_factory import get_llm
from app.services.email.service import send_email_smtp
from app.services.email_credentials import get_email_credentials, get_oauth_token

from ._provider_tools import _resolve_smtp_attachments, build_real_tools
from .prompts import build_system_prompt
from .tools import _load_attachments, build_tools_list

logger = logging.getLogger(__name__)


class EmailAgentResult:
    def __init__(self, action: str, success: bool, messages: list, error: str | None):
        self.action = action
        self.success = success
        self.extracted_data = {"messages_processed": messages}
        self.error = error
        self.validation_errors: list = []
        self.validation_warnings: list = []


def _build_provider_note(providers: dict, available_names: list, is_mock: bool) -> str:
    """Construye la nota de proveedores para el system prompt del agente."""
    if is_mock:
        return "NOTA: No hay credenciales de email configuradas. Usas datos de demostración."
    providers_info = ", ".join(available_names)
    if len(providers) == 1:
        return f"Proveedor de correo conectado: {providers_info}. Usa este proveedor para todas las operaciones."
    return (
        f"Proveedores de correo disponibles: {providers_info}.\n"
        "IMPORTANTE: Si el usuario especifica un proveedor (Gmail, Outlook, etc.), "
        "usa ese directamente. Si el usuario NO especifica qué proveedor usar, "
        "DEBES preguntarle desde cuál quiere operar antes de ejecutar la acción. "
        "Ejemplo: '¿Quieres que use Gmail o Outlook para esto?'"
    )


def _build_graph(tools_list, mode_note: str = ""):
    """Compila el grafo LangGraph con la lista de tools recibida."""
    local_llm = get_llm(temperature=0)
    local_llm_with_tools = local_llm.bind_tools(tools_list)

    async def agent_node(state: AgentState):
        extra_init_messages = []
        if "messages" not in state or not state["messages"]:
            sys_msg = SystemMessage(
                content=build_system_prompt(mode_note, state.get("tenant_id", ""))
            )
            user_msg = HumanMessage(content=state.get("current_intent", state["user_intent"]))
            extra_init_messages = [sys_msg, user_msg]
            state["messages"] = extra_init_messages

        response = await local_llm_with_tools.ainvoke(state["messages"])

        result_log = StepResult(
            step_id=f"email_step_{datetime.now().timestamp()}",
            description="Procesando correos electrónicos...",
            status="completed",
            action_taken=(
                "Invocando herramientas de correo"
                if response.tool_calls
                else (
                    response.content
                    if isinstance(response.content, str)
                    else "Operación de email completada."
                )
            ),
        )

        if "agent_results" not in state:
            state["agent_results"] = []
        state["agent_results"].append(result_log.model_dump())
        return {
            "messages": extra_init_messages + [response],
            "agent_results": state["agent_results"],
        }

    def finalize_node(state: AgentState):
        last_msg = state["messages"][-1]
        final_result = StepResult(
            step_id="email_final",
            description="Agente Email ha finalizado sus operaciones.",
            status="completed",
            action_taken=(
                last_msg.content
                if isinstance(last_msg.content, str)
                else "Operaciones de email completadas."
            ),
        )
        return {"status": "done", "agent_results": [final_result.model_dump()]}

    wf = StateGraph(AgentState)
    wf.add_node("email_agent", agent_node)
    wf.add_node("tools", ToolNode(tools_list))
    wf.add_node("finalize", finalize_node)

    wf.set_entry_point("email_agent")
    wf.add_conditional_edges("email_agent", tools_condition)
    wf.add_edge("tools", "email_agent")

    return wf.compile()


async def send_email_direct(
    tenant_id: str,
    to: str,
    subject: str,
    body: str,
    attachment_ids: list[str] | None = None,
) -> str:
    """
    Envía un email real usando las credenciales del tenant (gmail > outlook > smtp).
    Usable desde otros agentes sin pasar por el grafo LangGraph.
    """
    gmail_token = await get_oauth_token(tenant_id, "gmail")
    outlook_token = await get_oauth_token(tenant_id, "outlook")
    imap_creds = await get_email_credentials(tenant_id)

    attachments = await _load_attachments(tenant_id, attachment_ids)
    attach_msg = f" con {len(attachments)} adjuntos" if attachments else ""

    try:
        if gmail_token:
            from app.integrations.gmail_client import GmailClient

            client = GmailClient(gmail_token)
            try:
                await client.send_message(
                    to=to, subject=subject, body=body, attachments=attachments or None
                )
                return f"Correo enviado via Gmail{attach_msg}\nAsunto: {subject}\nPara: {to}"
            finally:
                await client.close()
        elif outlook_token:
            from app.integrations.outlook_client import OutlookClient

            client = OutlookClient(outlook_token)
            try:
                await client.send_message(
                    to=to, subject=subject, body=body, attachments=attachments or None
                )
                return f"Correo enviado via Outlook{attach_msg}\nAsunto: {subject}\nPara: {to}"
            finally:
                await client.close()
        elif imap_creds:
            attachment_paths = await _resolve_smtp_attachments(tenant_id, attachment_ids or [])
            result = send_email_smtp(
                imap_creds, to=to, subject=subject, body=body, attachment_paths=attachment_paths
            )
            if result["success"]:
                return f"Correo enviado via SMTP{attach_msg}\nAsunto: {subject}\nPara: {to}"
            else:
                return f"Error SMTP: {result['message']}"
        else:
            return "[SIN CREDENCIALES] No hay proveedor de email configurado para este tenant."
    except Exception as e:
        return f"Error al enviar correo: {e}"


async def run_email_agent(
    user_intent: str,
    tenant_id: str,
    task_id: str | None = None,
) -> EmailAgentResult:
    """
    Punto de entrada del email agent.
    Detecta qué proveedores de correo están disponibles (Gmail OAuth, Outlook OAuth, IMAP/SMTP)
    y crea tools con un parámetro `provider` para que el LLM elija según la intención del usuario.
    """
    providers: dict[str, str] = {}

    gmail_token = await get_oauth_token(tenant_id, "gmail")
    if gmail_token:
        providers["gmail"] = gmail_token

    outlook_token = await get_oauth_token(tenant_id, "outlook")
    if outlook_token:
        providers["outlook"] = outlook_token

    imap_creds = await get_email_credentials(tenant_id)
    if imap_creds:
        providers["imap"] = "imap"

    is_mock = len(providers) == 0
    default_provider = next(iter(providers), None)
    available_names = list(providers.keys())

    if is_mock:
        logger.warning(
            "[EMAIL] Tenant %s sin credenciales de email — usando datos DEMO. Las operaciones NO son reales.",
            tenant_id,
        )

    if not is_mock:
        real_tools = build_real_tools(providers, imap_creds, default_provider)
        tools_list = build_tools_list(*real_tools)
    else:
        tools_list = build_tools_list()

    mode_note = _build_provider_note(providers, available_names, is_mock)
    graph = _build_graph(tools_list, mode_note)

    state = {
        "user_intent": user_intent,
        "current_intent": user_intent,
        "tenant_id": tenant_id,
        "task_id": task_id,
        "messages": [],
        "agent_results": [],
    }

    try:
        result_state = await graph.ainvoke(state, config={"recursion_limit": 50})
    except Exception as e:
        logger.exception("Error ejecutando grafo del email agent")
        return EmailAgentResult(
            action=f"Error interno del agente de email: {e}",
            success=False,
            messages=[],
            error=str(e),
        )

    agent_results = result_state.get("agent_results", [])
    final_action = agent_results[-1]["action_taken"] if agent_results else "Sin resultado"
    return EmailAgentResult(
        action=final_action,
        success=True,
        messages=agent_results,
        error="[DEMO] No hay credenciales de email configuradas. Los correos mostrados son de demostración."
        if is_mock
        else None,
    )
