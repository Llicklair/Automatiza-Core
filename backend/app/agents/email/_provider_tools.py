"""Dynamic tool factory for email providers (Gmail, Outlook, IMAP/SMTP).

Tools are built at runtime because they close over provider tokens detected per tenant.
"""

import logging
import os
import uuid

from langchain_core.tools import tool
from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models.models import TenantDocument
from app.services.email.service import read_inbox, read_unread, send_email_smtp

from .tools import _load_attachments

logger = logging.getLogger(__name__)


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


def build_real_tools(
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
                    lines = [
                        f"- De: {m['from']}\n  Fecha: {m['date']}\n  Asunto: {m['subject']}\n  Resumen: {m['snippet']}"
                        for m in msgs
                    ]
                    return f"Correos en Gmail ({len(msgs)}):\n\n" + "\n\n".join(lines)
                finally:
                    await client.close()
            elif provider == "outlook":
                client = OutlookClient(providers["outlook"])
                try:
                    msgs = await client.list_messages(top=max_results)
                    if not msgs:
                        return "Bandeja de entrada de Outlook vacía."
                    lines = [
                        f"- De: {m['from_name'] or m['from']}\n  Fecha: {m['date']}\n  Asunto: {m['subject']}\n  Resumen: {m['snippet']}"
                        for m in msgs
                    ]
                    return f"Correos en Outlook ({len(msgs)}):\n\n" + "\n\n".join(lines)
                finally:
                    await client.close()
            else:  # imap
                msgs = read_inbox(imap_creds, max_results=max_results)
                if not msgs:
                    return "Bandeja de entrada IMAP vacía."
                lines = [
                    f"- De: {m.from_address}\n  Fecha: {m.date}\n  Asunto: {m.subject}\n  Cuerpo: {m.body[:500]}"
                    for m in msgs
                ]
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
                    lines = [
                        f"- De: {m['from']}\n  Fecha: {m['date']}\n  Asunto: {m['subject']}\n  Resumen: {m['snippet']}"
                        for m in msgs
                    ]
                    return f"Correos no leídos en Gmail ({len(msgs)}):\n\n" + "\n\n".join(lines)
                finally:
                    await client.close()
            elif provider == "outlook":
                client = OutlookClient(providers["outlook"])
                try:
                    msgs = await client.list_messages(top=max_results, search="isRead:false")
                    if not msgs:
                        return "No hay correos no leídos en Outlook."
                    lines = [
                        f"- De: {m['from_name'] or m['from']}\n  Fecha: {m['date']}\n  Asunto: {m['subject']}\n  Resumen: {m['snippet']}"
                        for m in msgs
                    ]
                    return f"Correos no leídos en Outlook ({len(msgs)}):\n\n" + "\n\n".join(lines)
                finally:
                    await client.close()
            else:  # imap
                msgs = read_unread(imap_creds, max_results=max_results)
                if not msgs:
                    return "No hay correos no leídos (IMAP)."
                lines = [
                    f"- De: {m.from_address}\n  Fecha: {m.date}\n  Asunto: {m.subject}\n  Cuerpo: {m.body[:500]}"
                    for m in msgs
                ]
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
                    await client.send_message(
                        to=to, subject=subject, body=body, attachments=attachments or None
                    )
                    return f"Correo enviado via Gmail{attach_msg}\nAsunto: {subject}\nPara: {to}"
                finally:
                    await client.close()
            elif provider == "outlook":
                client = OutlookClient(providers["outlook"])
                try:
                    await client.send_message(
                        to=to, subject=subject, body=body, attachments=attachments or None
                    )
                    return f"Correo enviado via Outlook{attach_msg}\nAsunto: {subject}\nPara: {to}"
                finally:
                    await client.close()
            else:  # imap/smtp
                attachment_paths = await _resolve_smtp_attachments(tenant_id, attachment_ids or [])
                result = send_email_smtp(
                    imap_creds, to=to, subject=subject, body=body, attachment_paths=attachment_paths
                )
                if result["success"]:
                    return (
                        f"Correo enviado via IMAP/SMTP{attach_msg}\nAsunto: {subject}\nPara: {to}"
                    )
                else:
                    return f"Error SMTP: {result['message']}"
        except Exception as e:
            return f"Error al enviar correo ({provider}): {e}"

    return check_inbox_real, check_unread_real, send_email_real
