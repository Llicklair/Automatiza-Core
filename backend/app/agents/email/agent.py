"""
Agente gestor de correos electrónicos.
Lee la bandeja de entrada y envía correos usando IMAP/SMTP real (con fallback a mock).
Si el tenant tiene credenciales de email configuradas → usa el servidor real.
Si no → usa datos de demostración para no romper el flujo.
"""

import logging
import os
import uuid
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from sqlalchemy import select

from app.agents.base import AgentState
from app.agents.types import StepResult
from app.core.llm_factory import get_llm
from app.db.base import AsyncSessionLocal
from app.db.models.models import TenantDocument
from app.services.email.service import read_inbox, read_unread, send_email_smtp

from .tools import (
    _get_email_credentials,
    _get_oauth_token,
    _load_attachments,
    build_tools_list,
    check_inbox,
    check_unread,
    send_email,
)

logger = logging.getLogger(__name__)


class EmailAgentResult:
    def __init__(self, action: str, success: bool, messages: list, error: str | None):
        self.action = action
        self.success = success
        self.extracted_data = {"messages_processed": messages}
        self.error = error
        self.validation_errors: list = []
        self.validation_warnings: list = []


async def _resolve_smtp_attachments(tenant_id: str, attachment_ids: list[str]) -> list[str]:
    """Resuelve IDs de documentos a rutas en disco para adjuntos SMTP."""
    paths = []
    async with AsyncSessionLocal() as db:
        for doc_id in attachment_ids:
            try:
                res = await db.execute(
                    select(TenantDocument.file_path).where(
                        TenantDocument.id == uuid.UUID(doc_id),
                        TenantDocument.tenant_id == uuid.UUID(tenant_id),
                    )
                )
                path = res.scalar_one_or_none()
                if path and os.path.exists(path):
                    paths.append(path)
            except Exception as e:
                logger.warning("Error resolviendo ruta de adjunto doc_id=%s: %s", doc_id, e)
    return paths


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
                content=(
                    "Eres el Agente Gestor de Correo Electrónico. "
                    f"{mode_note}\n\n"
                    "Tus herramientas disponibles:\n"
                    "1. `check_inbox`: Lee los correos más recientes. Acepta `provider` para elegir cuenta.\n"
                    "2. `check_unread`: Lee solo los correos no leídos. Acepta `provider`.\n"
                    "3. `send_email`: Envía un correo. Acepta `provider` para elegir desde qué cuenta enviar. "
                    "Puedes adjuntar archivos pasando una lista de `attachment_ids` (obtenidos con `list_tenant_documents`).\n"
                    "4. `create_document`: Archiva información extraída de correos en el Gestor Documental "
                    "(usa category='correos').\n"
                    "5. `list_tenant_documents`: Lista documentos archivados. "
                    "Úsala para encontrar el ID de una factura, nómina o informe que quieras enviar como adjunto.\n"
                    "6. `get_document_content`: Lee el contenido de un documento archivado.\n"
                    "7. Consultar la memoria del tenant con `get_tenant_knowledge` (ej: buscar contactos o preferencias).\n"
                    "8. Guardar nuevos hechos en la memoria con `upsert_tenant_knowledge`.\n\n"
                    "IMPORTANTE: Revisa siempre el 'Contexto de pasos anteriores' para ver si otros agentes han "
                    "generado documentos (como `document_id` de una factura). Si el usuario pide enviar algo "
                    "que acaba de ser creado, usa esos IDs automáticamente.\n\n"
                    f"ID del Tenant actual: {state.get('tenant_id')}.\n"
                    "Procesa la intención del usuario usando las herramientas que necesites. "
                    "Responde siempre en español con un resumen claro de lo que has hecho."
                )
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
    from app.services.email.service import send_email_smtp

    gmail_token = await _get_oauth_token(tenant_id, "gmail")
    outlook_token = await _get_oauth_token(tenant_id, "outlook")
    imap_creds = await _get_email_credentials(tenant_id)

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


def _build_real_tools(
    providers: dict[str, str],
    imap_creds: object,
    default_provider: str | None,
):
    """Construye las tools LangChain reales para los proveedores disponibles.
    Cierra sobre `providers` e `imap_creds` para evitar re-detectarlos en cada llamada.
    """
    from app.integrations.gmail_client import GmailClient
    from app.integrations.outlook_client import OutlookClient

    provider_desc = ", ".join(f'"{p}"' for p in providers)

    @tool
    async def check_inbox_real(
        tenant_id: str, provider: str = default_provider, max_results: int = 10
    ) -> str:
        """Lee los correos más recientes de la bandeja de entrada.
        Args:
            tenant_id: ID del tenant
            provider: Proveedor de correo a usar
            max_results: Máximo de correos a recuperar
        """
        if provider not in providers:
            return f"Error: proveedor '{provider}' no disponible. Usa uno de: {provider_desc}"
        try:
            if provider == "gmail":
                client = GmailClient(providers["gmail"])
                try:
                    msgs = await client.list_messages(max_results=max_results)
                    if not msgs:
                        return "Bandeja de entrada de Gmail vacía."
                    lines = [f"- De: {m['from']}\n  Fecha: {m['date']}\n  Asunto: {m['subject']}\n  Resumen: {m['snippet']}" for m in msgs]
                    return f"Correos en Gmail ({len(msgs)}):\n\n" + "\n\n".join(lines)
                finally:
                    await client.close()
            elif provider == "outlook":
                client = OutlookClient(providers["outlook"])
                try:
                    msgs = await client.list_messages(top=max_results)
                    if not msgs:
                        return "Bandeja de entrada de Outlook vacía."
                    lines = [f"- De: {m['from_name'] or m['from']}\n  Fecha: {m['date']}\n  Asunto: {m['subject']}\n  Resumen: {m['snippet']}" for m in msgs]
                    return f"Correos en Outlook ({len(msgs)}):\n\n" + "\n\n".join(lines)
                finally:
                    await client.close()
            else:  # imap
                msgs = read_inbox(imap_creds, max_results=max_results)
                if not msgs:
                    return "Bandeja de entrada IMAP vacía."
                lines = [f"- De: {m.from_address}\n  Fecha: {m.date}\n  Asunto: {m.subject}\n  Cuerpo: {m.body[:500]}" for m in msgs]
                return f"Correos IMAP ({len(msgs)}):\n\n" + "\n\n".join(lines)
        except Exception as e:
            return f"Error al leer bandeja ({provider}): {e}"

    @tool
    async def check_unread_real(
        tenant_id: str, provider: str = default_provider, max_results: int = 10
    ) -> str:
        """Lee solo los correos NO LEÍDOS de la bandeja de entrada.
        Args:
            tenant_id: ID del tenant
            provider: Proveedor de correo a usar
            max_results: Máximo de correos no leídos a recuperar
        """
        if provider not in providers:
            return f"Error: proveedor '{provider}' no disponible. Usa uno de: {provider_desc}"
        try:
            if provider == "gmail":
                client = GmailClient(providers["gmail"])
                try:
                    msgs = await client.list_messages(query="is:unread", max_results=max_results)
                    if not msgs:
                        return "No hay correos no leídos en Gmail."
                    lines = [f"- De: {m['from']}\n  Fecha: {m['date']}\n  Asunto: {m['subject']}\n  Resumen: {m['snippet']}" for m in msgs]
                    return f"Correos no leídos en Gmail ({len(msgs)}):\n\n" + "\n\n".join(lines)
                finally:
                    await client.close()
            elif provider == "outlook":
                client = OutlookClient(providers["outlook"])
                try:
                    msgs = await client.list_messages(top=max_results, search="isRead:false")
                    if not msgs:
                        return "No hay correos no leídos en Outlook."
                    lines = [f"- De: {m['from_name'] or m['from']}\n  Fecha: {m['date']}\n  Asunto: {m['subject']}\n  Resumen: {m['snippet']}" for m in msgs]
                    return f"Correos no leídos en Outlook ({len(msgs)}):\n\n" + "\n\n".join(lines)
                finally:
                    await client.close()
            else:  # imap
                msgs = read_unread(imap_creds, max_results=max_results)
                if not msgs:
                    return "No hay correos no leídos (IMAP)."
                lines = [f"- De: {m.from_address}\n  Fecha: {m.date}\n  Asunto: {m.subject}\n  Cuerpo: {m.body[:500]}" for m in msgs]
                return f"Correos no leídos IMAP ({len(msgs)}):\n\n" + "\n\n".join(lines)
        except Exception as e:
            return f"Error al leer no leídos ({provider}): {e}"

    @tool
    async def send_email_real(
        tenant_id: str,
        to: str,
        subject: str,
        body: str,
        provider: str = default_provider,
        attachment_ids: list[str] | None = None,
    ) -> str:
        """Envía un correo electrónico al destinatario indicado.
        Args:
            tenant_id: ID del tenant
            to: Dirección de correo electrónico del destinatario
            subject: Asunto del correo
            body: Cuerpo del correo en texto plano
            provider: Proveedor de correo a usar
            attachment_ids: Opcional. Lista de IDs de documentos a adjuntar.
        """
        if provider not in providers:
            return f"Error: proveedor '{provider}' no disponible. Usa uno de: {provider_desc}"
        if isinstance(attachment_ids, str):
            attachment_ids = [attachment_ids] if attachment_ids else None
        attachments = await _load_attachments(tenant_id, attachment_ids)
        attach_msg = f" con {len(attachments)} adjuntos" if attachments else ""
        try:
            if provider == "gmail":
                client = GmailClient(providers["gmail"])
                try:
                    await client.send_message(to=to, subject=subject, body=body, attachments=attachments or None)
                    return f"Correo enviado via Gmail{attach_msg}\nAsunto: {subject}\nPara: {to}"
                finally:
                    await client.close()
            elif provider == "outlook":
                client = OutlookClient(providers["outlook"])
                try:
                    await client.send_message(to=to, subject=subject, body=body, attachments=attachments or None)
                    return f"Correo enviado via Outlook{attach_msg}\nAsunto: {subject}\nPara: {to}"
                finally:
                    await client.close()
            else:  # imap/smtp
                attachment_paths = await _resolve_smtp_attachments(tenant_id, attachment_ids or [])
                result = send_email_smtp(imap_creds, to=to, subject=subject, body=body, attachment_paths=attachment_paths)
                if result["success"]:
                    return f"Correo enviado via IMAP/SMTP{attach_msg}\nAsunto: {subject}\nPara: {to}"
                else:
                    return f"Error SMTP: {result['message']}"
        except Exception as e:
            return f"Error al enviar correo ({provider}): {e}"

    return check_inbox_real, check_unread_real, send_email_real


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
    # ── Detectar todos los proveedores disponibles ────────────────────────
    providers: dict[str, str] = {}

    gmail_token = await _get_oauth_token(tenant_id, "gmail")
    if gmail_token:
        providers["gmail"] = gmail_token

    outlook_token = await _get_oauth_token(tenant_id, "outlook")
    if outlook_token:
        providers["outlook"] = outlook_token

    imap_creds = await _get_email_credentials(tenant_id)
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
        real_tools = _build_real_tools(providers, imap_creds, default_provider)
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
        return EmailAgentResult(action=f"Error interno del agente de email: {e}", success=False, messages=[], error=str(e))

    agent_results = result_state.get("agent_results", [])
    final_action = agent_results[-1]["action_taken"] if agent_results else "Sin resultado"
    return EmailAgentResult(
        action=final_action,
        success=True,
        messages=agent_results,
        error="[DEMO] No hay credenciales de email configuradas. Los correos mostrados son de demostración." if is_mock else None,
    )
