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
# Movidas a app.services.email_credentials (las consumen rutas y otros agentes).


async def _load_attachments(
    tenant_id: str, attachment_ids: list[str] | None
) -> list[tuple[str, bytes]]:
    """Load document attachments from DB by their IDs."""
    if not attachment_ids:
        return []
    import os
    import uuid

    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    from app.db.models.models import TenantDocument

    attachments = []
    async with AsyncSessionLocal() as db:
        for doc_id in attachment_ids:
            try:
                res = await db.execute(
                    select(TenantDocument.file_path, TenantDocument.file_name).where(
                        TenantDocument.id == uuid.UUID(doc_id),
                        TenantDocument.tenant_id == uuid.UUID(tenant_id),
                    )
                )
                row = res.one_or_none()
                if not row:
                    logger.warning(
                        "Adjunto doc_id=%s no encontrado para tenant=%s", doc_id, tenant_id
                    )
                    continue
                if not row.file_path or not os.path.exists(row.file_path):
                    logger.warning(
                        "Adjunto doc_id=%s con file_path inválido: %s", doc_id, row.file_path
                    )
                    continue
                with open(row.file_path, "rb") as f:
                    attachments.append(
                        (row.file_name or os.path.basename(row.file_path), f.read())
                    )
            except Exception as _e:
                logger.warning(
                    "Error leyendo adjunto doc_id=%s tenant=%s: %s", doc_id, tenant_id, _e
                )
                continue
    return attachments


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
def send_email(
    tenant_id: str,
    to: str,
    subject: str,
    body: str,
    attachment_ids: list[str] | str | None = None,
) -> str:
    """
    Envía un correo electrónico al destinatario indicado, permitiendo adjuntar documentos.
    Args:
        tenant_id: ID del tenant
        to: Dirección de correo electrónico del destinatario
        subject: Asunto del correo
        body: Cuerpo del correo en texto plano
        attachment_ids: Opcional. Lista de IDs de documentos del Escanear
            (TenantDocument) a adjuntar. Acepta también un único ID como
            string — los LLM suelen omitir los corchetes con un solo elemento.
    """
    if isinstance(attachment_ids, str):
        attachment_ids = [attachment_ids] if attachment_ids else None
    attachments_str = f" con {len(attachment_ids)} adjuntos" if attachment_ids else ""
    return (
        f"[DEMO] Correo '{subject}' preparado para {to}{attachments_str}.\n"
        f"Contenido:\n{body}\n\n"
        "(Configura las credenciales de email en Integraciones para envíos reales)"
    )


def build_tools_list(real_check_fn=None, real_unread_fn=None, real_send_fn=None):
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
