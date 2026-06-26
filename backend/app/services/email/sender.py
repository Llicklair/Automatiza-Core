"""
Email-sender service — public API para que cualquier capa (agentes, routes,
otros services) envíe emails sin importar directamente del agente de email.

Cumple la regla de arquitectura "agentes NUNCA importan otros agentes":
billing/hr/etc llaman a este service, no a `app.agents.email`.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid

from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models.models import TenantDocument
from app.services.email.credentials import get_email_credentials, get_oauth_token
from app.services.email.service import send_email_smtp

logger = logging.getLogger(__name__)


async def load_attachments(
    tenant_id: str, attachment_ids: list[str] | None
) -> list[tuple[str, bytes]]:
    """Carga adjuntos (nombre, bytes) desde TenantDocument por sus IDs."""
    if not attachment_ids:
        return []
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


async def resolve_smtp_attachments(tenant_id: str, attachment_ids: list[str]) -> list[str]:
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


async def send_email(
    tenant_id: str,
    to: str,
    subject: str,
    body: str,
    attachment_ids: list[str] | None = None,
) -> str:
    """Envía un email usando las credenciales del tenant (gmail > outlook > smtp).

    Devuelve un string descriptivo del resultado (success o error). No lanza
    excepciones — los errores se reportan como string para no romper agentes.
    """
    gmail_token = await get_oauth_token(tenant_id, "gmail")
    outlook_token = await get_oauth_token(tenant_id, "outlook")
    imap_creds = await get_email_credentials(tenant_id)

    attachments = await load_attachments(tenant_id, attachment_ids)
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
            attachment_paths = await resolve_smtp_attachments(tenant_id, attachment_ids or [])
            result = await asyncio.to_thread(
                send_email_smtp,
                imap_creds,
                to=to,
                subject=subject,
                body=body,
                attachment_paths=attachment_paths,
            )
            if result["success"]:
                return f"Correo enviado via SMTP{attach_msg}\nAsunto: {subject}\nPara: {to}"
            else:
                return f"Error SMTP: {result['message']}"
        else:
            return "[SIN CREDENCIALES] No hay proveedor de email configurado para este tenant."
    except Exception as e:
        return f"Error al enviar correo: {e}"


# send_email NO lanza: comunica el resultado como string. Un FALLO empieza por una
# de estas marcas; cualquier otro retorno (incluido None de un mock, o
# "Correo enviado via …") se considera ÉXITO. Lo usa send_campaign para contar
# correctamente sent vs failed (antes contaba como enviado todo lo que no lanzara).
_SEND_ERROR_PREFIXES = ("Error", "[SIN CREDENCIALES]")


def send_failed(result: object) -> bool:
    """True si el string devuelto por send_email indica un fallo de envío."""
    return isinstance(result, str) and result.startswith(_SEND_ERROR_PREFIXES)
