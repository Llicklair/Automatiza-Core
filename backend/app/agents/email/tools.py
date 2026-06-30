"""
Herramientas del agente de correo electrónico.
Incluye mock fallback y funciones de credenciales.
"""

import logging

from langchain_core.tools import tool

from app.agents.agent_tools.documents import (
    create_document,
    get_document_content,
    list_tenant_documents,
)
from app.agents.agent_tools.knowledge import get_tenant_knowledge, upsert_tenant_knowledge

logger = logging.getLogger(__name__)

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

# ─── Credenciales de email del tenant ─────────────────────────────────────────
# Movidas a app.services.email.credentials (las consumen rutas y otros agentes).
# Carga de adjuntos movida a app.services.email.sender.


# ─── Herramientas mock (fallback) ─────────────────────────────────────────────


@tool
def check_inbox(tenant_id: str, max_results: int = 10) -> str:
    """
    Revisa la bandeja de entrada de correos electrónicos.
    Lee los mensajes más recientes y devuelve su remitente, asunto y cuerpo.
    Args:
        tenant_id: ID del tenant
        max_results: Máximo de correos a recuperar (por defecto 10)
    """
    lines = [
        f"- [ID: {em['id']}] De: {em['from']} | Fecha: {em['date']}\n"
        f"  Asunto: {em['subject']}\n"
        f"  Cuerpo: {em['body']}"
        for em in MOCK_EMAILS[:max_results]
    ]
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
def send_email(
    tenant_id: str,
    to: str,
    subject: str,
    body: str,
    attachment_ids: list[str] | str | None = None,
    confirm: bool = False,
) -> str:
    """
    Envía un correo electrónico al destinatario indicado, permitiendo adjuntar documentos.
    IMPORTANTE: llama siempre con confirm=False primero para mostrar el borrador al usuario.
    Solo llama con confirm=True cuando el usuario haya aprobado explícitamente el envío.
    Args:
        tenant_id: ID del tenant
        to: Dirección de correo electrónico del destinatario
        subject: Asunto del correo
        body: Cuerpo del correo en texto plano
        attachment_ids: Opcional. Lista de IDs de documentos del Escanear
            (TenantDocument) a adjuntar. Acepta también un único ID como
            string — los LLM suelen omitir los corchetes con un solo elemento.
        confirm: False = mostrar borrador sin enviar (por defecto). True = enviar.
    """
    if isinstance(attachment_ids, str):
        attachment_ids = [attachment_ids] if attachment_ids else None
    attachments_str = f" con {len(attachment_ids)} adjuntos" if attachment_ids else ""

    preview = (
        f"Borrador de correo:\n"
        f"  Para: {to}\n"
        f"  Asunto: {subject}\n"
        f"  Cuerpo:\n{body}"
        + (f"\n  Adjuntos: {len(attachment_ids)} documento(s)" if attachment_ids else "")
    )
    if not confirm:
        return (
            f"{preview}\n\n"
            "¿Confirmas el envío? Responde 'sí, envía' para proceder o 'no' para cancelar.\n"
            "(DEMO: configura credenciales de email en Integraciones para envíos reales)"
        )
    # NO afirmar "enviado": sin credenciales no se envía nada. Antes devolvía
    # "[DEMO] Correo enviado a ..." y el usuario/LLM lo daba por enviado (exito
    # silencioso falso). Hay que dejar inequivoco que el correo NO salió.
    return (
        f"⚠ NO se envió el correo '{subject}' a {to}{attachments_str}: no hay "
        "credenciales de email configuradas (modo demo). Configúralas en "
        "Integraciones para poder enviar correos de verdad."
    )


def build_tools_list(
    real_check_fn=None,
    real_unread_fn=None,
    real_send_fn=None,
    real_reply_fn=None,
    real_markread_fn=None,
):
    """Devuelve la lista de tools con las funciones reales o mock según disponibilidad.

    reply/mark_read solo existen en modo real (Gmail/Outlook): sin credenciales no se exponen.
    """
    extra = [t for t in (real_reply_fn, real_markread_fn) if t is not None]
    return [
        real_check_fn or check_inbox,
        real_unread_fn or check_unread,
        real_send_fn or send_email,
        *extra,
        create_document,
        list_tenant_documents,
        get_document_content,
        get_tenant_knowledge,
        upsert_tenant_knowledge,
    ]
