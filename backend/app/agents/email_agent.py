"""
Agente gestor de correos electrónicos.
Lee la bandeja de entrada y envía correos usando IMAP/SMTP real (con fallback a mock).
Si el tenant tiene credenciales de email configuradas → usa el servidor real.
Si no → usa datos de demostración para no romper el flujo.
"""
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.core.config import settings
from app.core.llm_factory import get_llm

from app.agents.agent_tools.documents import (
    create_document,
    get_document_content,
    list_tenant_documents,
)
from app.agents.agent_tools.knowledge import get_tenant_knowledge, upsert_tenant_knowledge
from app.agents.base import AgentState
from app.agents.types import StepResult

# ─── Mock fallback (cuando no hay credenciales configuradas) ──────────────────

MOCK_EMAILS = [
    {
        "id": "eml_1",
        "from": "juan.cliente@acme.com",
        "subject": "Aceptación de Presupuesto - Proyecto Web",
        "body": "Hola,\nPor la presente aceptamos el presupuesto enviado la semana pasada para la renovación de la página web por 2.500€. Por favor enviad la primera factura para iniciar el proyecto.\n\nSaludos,\nJuan",
        "date": "2025-10-15T10:30:00Z",
    },
    {
        "id": "eml_2",
        "from": "rrhh@proveedor-servicios.es",
        "subject": "Candidatos para puesto de marketing",
        "body": "Hola, os adjunto en texto los perfiles de los dos nuevos candidatos: Carlos Ruiz (Junior, 22k) y Ana García (Senior, 35k). Revisadlo y decidimos mañana.",
        "date": "2025-10-16T09:15:00Z",
    },
]

# ─── Carga de credenciales de email del tenant ────────────────────────────────

async def _get_email_credentials(tenant_id: str):
    """
    Carga las credenciales de email del tenant desde la BD.
    Devuelve EmailCredentials si están configuradas, None si no.
    """
    import uuid
    from sqlalchemy import select
    from app.db.base import AsyncSessionLocal
    from app.db.models.models import TenantIntegration
    from app.services.encryption import decrypt_credentials
    from app.services.email_service import credentials_from_dict

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(TenantIntegration).where(
                    TenantIntegration.tenant_id == uuid.UUID(tenant_id),
                    TenantIntegration.integration_type == "email",
                    TenantIntegration.is_active.is_(True),
                )
            )
            integration = result.scalar_one_or_none()

        if not integration:
            return None

        creds_dict = decrypt_credentials(integration.encrypted_credentials)
        return credentials_from_dict(creds_dict)
    except Exception:
        return None


# ─── Herramientas del agente ──────────────────────────────────────────────────

# Se definen como closures para poder inyectar las credenciales en tiempo de ejecución.
# El LLM las invoca por nombre — el runner las sobreescribe antes de compilar el grafo.

@tool
def check_inbox(tenant_id: str, max_results: int = 10) -> str:
    """
    Revisa la bandeja de entrada de correos electrónicos.
    Lee los mensajes más recientes y devuelve su remitente, asunto y cuerpo.
    Args:
        tenant_id: ID del tenant
        max_results: Máximo de correos a recuperar (por defecto 10)
    """
    # Esta implementación es el fallback mock.
    # En run_email_agent se reemplaza por la versión real si hay credenciales.
    lines = []
    for em in MOCK_EMAILS[:max_results]:
        lines.append(
            f"- [ID: {em['id']}] De: {em['from']} | Fecha: {em['date']}\n"
            f"  Asunto: {em['subject']}\n"
            f"  Cuerpo: {em['body']}"
        )
    if not lines:
        return "Bandeja de entrada vacía."
    return "[DEMO] Correos en Bandeja de Entrada:\n\n" + "\n\n".join(lines)


@tool
def check_unread(tenant_id: str, max_results: int = 10) -> str:
    """
    Revisa solo los correos NO LEÍDOS de la bandeja de entrada.
    Args:
        tenant_id: ID del tenant
        max_results: Máximo de correos no leídos a recuperar
    """
    return check_inbox.invoke({"tenant_id": tenant_id, "max_results": max_results})


@tool
def send_email(tenant_id: str, to: str, subject: str, body: str, attachment_ids: list[str] | None = None) -> str:
    """
    Envía un correo electrónico al destinatario indicado, permitiendo adjuntar documentos.
    Args:
        tenant_id: ID del tenant
        to: Dirección de correo electrónico del destinatario
        subject: Asunto del correo
        body: Cuerpo del correo en texto plano
        attachment_ids: Opcional. Lista de IDs de documentos del Escanear (TenantDocument) a adjuntar.
    """
    # Fallback mock — se reemplaza por versión real en run_email_agent
    attachments_str = f" con {len(attachment_ids)} adjuntos" if attachment_ids else ""
    return (
        f"[DEMO] Correo '{subject}' preparado para {to}{attachments_str}.\n"
        f"Contenido:\n{body}\n\n"
        "(Configura las credenciales de email en Integraciones para envíos reales)"
    )


# ─── Nodos del grafo ──────────────────────────────────────────────────────────

def _build_tools_list(real_check_fn=None, real_unread_fn=None, real_send_fn=None):
    """Devuelve la lista de tools con las funciones reales o mock según disponibilidad."""
    return [
        real_check_fn or check_inbox,
        real_unread_fn or check_unread,
        real_send_fn or send_email,
        create_document,
        list_tenant_documents,
        get_document_content,
        get_tenant_knowledge,
        upsert_tenant_knowledge,
    ]


def _build_graph(tools_list):
    """Compila el grafo LangGraph con la lista de tools recibida."""
    local_llm = get_llm(temperature=0)
    local_llm_with_tools = local_llm.bind_tools(tools_list)

    async def agent_node(state: AgentState):
        extra_init_messages = []
        if "messages" not in state or not state["messages"]:
            has_real = any("DEMO" not in t.name for t in tools_list if hasattr(t, "name"))
            mode_note = "Estás conectado a la cuenta de correo real del tenant." if has_real else \
                        "NOTA: No hay credenciales de email configuradas. Usas datos de demostración."
            sys_msg = SystemMessage(
                content=(
                    "Eres el Agente Gestor de Correo Electrónico. "
                    f"{mode_note}\n\n"
                    "Tus herramientas disponibles:\n"
                    "1. `check_inbox`: Lee los correos más recientes de la bandeja de entrada.\n"
                    "2. `check_unread`: Lee solo los correos no leídos.\n"
                    "3. `send_email`: Envía un correo electrónico con asunto y cuerpo. "
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
                "Invocando herramientas de correo" if response.tool_calls
                else (response.content if isinstance(response.content, str) else "Operación de email completada.")
            ),
        )

        if "agent_results" not in state:
            state["agent_results"] = []
        state["agent_results"].append(result_log.model_dump())
        # Incluir los mensajes de inicialización en el return para que LangGraph
        # los acumule correctamente en el estado (add_messages reducer)
        return {"messages": extra_init_messages + [response], "agent_results": state["agent_results"]}

    def finalize_node(state: AgentState):
        last_msg = state["messages"][-1]
        final_result = StepResult(
            step_id="email_final",
            description="Agente Email ha finalizado sus operaciones.",
            status="completed",
            action_taken=(
                last_msg.content if isinstance(last_msg.content, str)
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


# ─── Runner principal ──────────────────────────────────────────────────────────

async def run_email_agent(
    user_intent: str,
    tenant_id: str,
    task_id: str | None = None,
) -> object:
    """
    Punto de entrada del email agent.
    1. Intenta cargar credenciales reales del tenant.
    2. Si las hay, crea tools con IMAP/SMTP real.
    3. Si no, usa mock para no bloquear el flujo.
    """
    from app.services.email_service import (
        EmailCredentials,
        read_inbox,
        read_unread,
        send_email_smtp,
    )

    credentials = await _get_email_credentials(tenant_id)

    if credentials:
        # ── Versión REAL ────────────────────────────────────────────────────
        creds_snapshot = credentials  # Capturar para el closure

        @tool
        def check_inbox_real(tenant_id: str, max_results: int = 10) -> str:
            """
            Lee los correos más recientes de la bandeja de entrada real del tenant.
            Args:
                tenant_id: ID del tenant
                max_results: Máximo de correos a recuperar
            """
            try:
                msgs = read_inbox(creds_snapshot, max_results=max_results)
                if not msgs:
                    return "Bandeja de entrada vacía."
                lines = []
                for m in msgs:
                    read_flag = "✓ Leído" if m.is_read else "● No leído"
                    lines.append(
                        f"- [ID: {m.id}] {read_flag}\n"
                        f"  De: {m.from_address}\n"
                        f"  Fecha: {m.date}\n"
                        f"  Asunto: {m.subject}\n"
                        f"  Cuerpo: {m.body[:500]}{'...' if len(m.body) > 500 else ''}"
                    )
                return f"Correos en Bandeja de Entrada ({len(msgs)} mensajes):\n\n" + "\n\n".join(lines)
            except Exception as e:
                return f"Error al leer la bandeja de entrada: {e}"

        @tool
        def check_unread_real(tenant_id: str, max_results: int = 10) -> str:
            """
            Lee solo los correos NO LEÍDOS de la bandeja de entrada real.
            Args:
                tenant_id: ID del tenant
                max_results: Máximo de correos no leídos a recuperar
            """
            try:
                msgs = read_unread(creds_snapshot, max_results=max_results)
                if not msgs:
                    return "No hay correos no leídos."
                lines = []
                for m in msgs:
                    lines.append(
                        f"- [ID: {m.id}] De: {m.from_address}\n"
                        f"  Fecha: {m.date}\n"
                        f"  Asunto: {m.subject}\n"
                        f"  Cuerpo: {m.body[:500]}{'...' if len(m.body) > 500 else ''}"
                    )
                return f"Correos NO leídos ({len(msgs)}):\n\n" + "\n\n".join(lines)
            except Exception as e:
                return f"Error al leer correos no leídos: {e}"

        @tool
        async def send_email_real(tenant_id: str, to: str, subject: str, body: str, attachment_ids: list[str] | None = None) -> str:
            """
            Envía un correo electrónico real al destinatario indicado, permitiendo adjuntar documentos.
            Args:
                tenant_id: ID del tenant
                to: Dirección de correo electrónico del destinatario
                subject: Asunto del correo
                body: Cuerpo del correo en texto plano
                attachment_ids: Opcional. Lista de IDs de documentos (TenantDocument) a adjuntar.
            """
            from app.db.base import AsyncSessionLocal
            from app.db.models.models import TenantDocument
            import uuid
            import os

            attachment_paths = []
            if attachment_ids:
                async with AsyncSessionLocal() as db:
                    for doc_id in attachment_ids:
                        try:
                            res = await db.execute(
                                select(TenantDocument.file_path).where(
                                    TenantDocument.id == uuid.UUID(doc_id),
                                    TenantDocument.tenant_id == uuid.UUID(tenant_id)
                                )
                            )
                            path = res.scalar_one_or_none()
                            if path and os.path.exists(path):
                                attachment_paths.append(path)
                        except Exception:
                            continue

            result = send_email_smtp(
                creds_snapshot, 
                to=to, 
                subject=subject, 
                body=body,
                attachment_paths=attachment_paths
            )
            
            if result["success"]:
                attach_msg = f" con {len(attachment_paths)} adjuntos" if attachment_paths else ""
                return f"✅ {result['message']}{attach_msg}\nAsunto: {subject}\nPara: {to}"
            else:
                return f"❌ {result['message']}"

        tools_list = _build_tools_list(check_inbox_real, check_unread_real, send_email_real)
    else:
        # ── Versión MOCK ────────────────────────────────────────────────────
        tools_list = _build_tools_list()

    graph = _build_graph(tools_list)

    state = {
        "user_intent": user_intent,
        "current_intent": user_intent,
        "tenant_id": tenant_id,
        "task_id": task_id,
        "messages": [],
        "agent_results": [],
    }

    result_state = await graph.ainvoke(state, config={"recursion_limit": 50})

    class EmailAgentResult:
        def __init__(self, action, success, messages, error):
            self.action = action
            self.success = success
            self.extracted_data = {"messages_processed": messages}
            self.error = error
            self.validation_errors = []
            self.validation_warnings = []

    agent_results = result_state.get("agent_results", [])
    final_action = agent_results[-1]["action_taken"] if agent_results else "Sin resultado"

    is_mock = credentials is None
    return EmailAgentResult(
        action=final_action,
        success=True,
        messages=agent_results,
        error="[DEMO] No hay credenciales de email configuradas. Los correos mostrados son de demostración." if is_mock else None,
    )
