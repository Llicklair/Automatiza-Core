"""
Business logic for Telegram messaging integration.

Services raise ValueError / LookupError — routes translate to HTTP responses.
"""

import asyncio
import logging
import secrets
from uuid import UUID as _UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.models import TenantIntegration
from app.integrations.telegram_client import TelegramClient
from app.services.encryption import decrypt_credentials, encrypt_credentials

logger = logging.getLogger(__name__)


# ─── Helpers ────────────────────────────────────────────────────────────────


async def send_reply(chat_id: int, text: str, reply_to_message_id: int | None = None):
    """Send a reply via Telegram bot."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN no configurado, no se puede responder")
        return
    client = TelegramClient(settings.TELEGRAM_BOT_TOKEN)
    try:
        await client.send_message(chat_id, text, reply_to_message_id=reply_to_message_id)
    except Exception as e:
        logger.error("Error enviando mensaje Telegram a chat %s: %s", chat_id, e)
    finally:
        await client.close()


async def find_integration_by_chat(db: AsyncSession, chat_id: int) -> TenantIntegration | None:
    """Find the active Telegram integration for a chat_id."""
    result = await db.execute(
        select(TenantIntegration).where(
            TenantIntegration.integration_type == "telegram",
            TenantIntegration.is_active.is_(True),
        )
    )
    for integration in result.scalars().all():
        config = integration.config or {}
        if config.get("chat_id") == chat_id:
            return integration
    return None


# ─── Webhook processing ────────────────────────────────────────────────────


def verify_webhook_secret(secret_header: str | None) -> bool:
    """Return True if secret token is valid (or not configured)."""
    if settings.TELEGRAM_WEBHOOK_SECRET:
        return TelegramClient.verify_secret(secret_header, settings.TELEGRAM_WEBHOOK_SECRET)
    return True


async def handle_link_command(
    db: AsyncSession,
    chat_id: int,
    username: str | None,
    first_name: str | None,
    link_token: str,
):
    """Link a Telegram chat to a tenant using the link token."""
    result = await db.execute(
        select(TenantIntegration).where(
            TenantIntegration.integration_type == "telegram",
            TenantIntegration.is_active.is_(False),
        )
    )
    for integration in result.scalars().all():
        try:
            creds = decrypt_credentials(integration.encrypted_credentials)
        except Exception:
            continue
        if creds.get("link_token") == link_token:
            creds["chat_id"] = chat_id
            creds["username"] = username or ""
            creds["first_name"] = first_name or ""
            creds.pop("link_token", None)
            integration.encrypted_credentials = encrypt_credentials(creds)
            integration.is_active = True
            integration.config = {"chat_id": chat_id, "username": username or ""}
            await db.commit()

            await send_reply(
                chat_id,
                (
                    "¡Vinculación exitosa! 🎉\n\n"
                    "Este chat está ahora conectado a tu empresa.\n"
                    "Puedes escribirme cualquier cosa: crear facturas, consultar datos, "
                    "gestionar empleados, etc.\n\n"
                    "Escribe tu primera solicitud para empezar."
                ),
            )
            return

    await send_reply(
        chat_id, "Token de vinculación inválido o expirado. Genera uno nuevo desde el panel web."
    )


async def send_typing_indicator(chat_id: int):
    """Send typing indicator via Telegram."""
    try:
        bot_token = settings.TELEGRAM_BOT_TOKEN
        client = TelegramClient(bot_token)
        await client.send_typing(chat_id)
        await client.close()
    except Exception:
        pass


async def process_and_reply(tenant_id: str, chat_id: int, text: str, reply_to: int):
    """Create a Task, dispatch to orchestrator, poll for result, and reply via Telegram."""
    try:
        from app.db.base import AsyncSessionLocal
        from app.db.models.models import Task
        from app.services.workflow.task_dispatch import dispatch_orchestrator

        # 1. Create task in DB
        async with AsyncSessionLocal() as db:
            task = Task(
                tenant_id=_UUID(tenant_id),
                created_by=None,
                domain="general",
                user_intent=text,
                status="pending",
                additional_metadata={"channel": "telegram", "chat_id": chat_id},
            )
            db.add(task)
            await db.commit()
            await db.refresh(task)
            task_id = str(task.id)

        # 2. Dispatch to orchestrator
        # Fase 3 (RLS): propagamos tenant_id al worker.
        await dispatch_orchestrator(task_id, tenant_id=str(tenant_id))

        # 3. Poll until task finishes (max 120s)
        response_text = "Tu solicitud está siendo procesada."
        for _ in range(60):
            await asyncio.sleep(2)
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Task).where(Task.id == _UUID(task_id)))
                task = result.scalar_one_or_none()
                if not task:
                    break
                if task.status in ("completed", "failed", "done"):
                    output = task.output_data or {}
                    if isinstance(output, dict):
                        resp = output.get("response", "")
                        if not resp:
                            agent_results = output.get("agent_results", [])
                            if agent_results:
                                last = agent_results[-1]
                                resp = last.get("action_taken", "") or last.get("description", "")
                        if resp:
                            response_text = resp
                        elif task.status == "failed":
                            response_text = "No he podido completar tu solicitud."
                        else:
                            response_text = "Solicitud procesada correctamente."
                    elif isinstance(output, str) and output:
                        response_text = output
                    break

        await send_reply(chat_id, response_text, reply_to_message_id=reply_to)

    except Exception as e:
        logger.exception("Error procesando mensaje Telegram para tenant %s: %s", tenant_id, e)
        await send_reply(chat_id, "Ha ocurrido un error procesando tu mensaje. Inténtalo de nuevo.")


# ─── Connection management ─────────────────────────────────────────────────


async def connect_telegram(db: AsyncSession, tenant_id) -> dict:
    """Generate a link token and upsert integration. Returns dict with link info."""
    if not settings.TELEGRAM_BOT_TOKEN:
        raise ValueError("Telegram no está configurado en el servidor")

    link_token = secrets.token_urlsafe(32)

    # Get bot username
    bot_username = None
    client = TelegramClient(settings.TELEGRAM_BOT_TOKEN)
    try:
        me = await client.get_me()
        bot_username = me.get("result", {}).get("username")
    except Exception as e:
        logger.warning("No se pudo obtener info del bot: %s", e)
    finally:
        await client.close()

    # Upsert integration (inactive until user does /start)
    result = await db.execute(
        select(TenantIntegration).where(
            TenantIntegration.tenant_id == tenant_id,
            TenantIntegration.integration_type == "telegram",
        )
    )
    existing = result.scalar_one_or_none()

    encrypted = encrypt_credentials({"link_token": link_token})

    if existing:
        existing.encrypted_credentials = encrypted
        existing.is_active = False
        existing.config = {}
    else:
        db.add(
            TenantIntegration(
                tenant_id=tenant_id,
                integration_type="telegram",
                encrypted_credentials=encrypted,
                is_active=False,
                config={},
            )
        )

    await db.commit()

    link_url = f"https://t.me/{bot_username}?start={link_token}" if bot_username else ""

    return {
        "link_url": link_url,
        "link_token": link_token,
        "bot_username": bot_username,
    }


async def disconnect_telegram(db: AsyncSession, tenant_id) -> dict:
    """Disconnect Telegram integration for a tenant. Raises LookupError if not found."""
    result = await db.execute(
        select(TenantIntegration).where(
            TenantIntegration.tenant_id == tenant_id,
            TenantIntegration.integration_type == "telegram",
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise LookupError("Integración de Telegram no encontrada")

    # Notify user in Telegram before disconnecting
    config = integration.config or {}
    chat_id = config.get("chat_id")
    if chat_id and settings.TELEGRAM_BOT_TOKEN:
        try:
            client = TelegramClient(settings.TELEGRAM_BOT_TOKEN)
            await client.send_message(
                chat_id,
                "Este chat ha sido desvinculado de la empresa. Ya no recibirás respuestas aquí.",
            )
            await client.close()
        except Exception:
            pass

    integration.is_active = False
    integration.config = {}
    await db.commit()
    return {"status": "desconectado"}


async def get_telegram_status(db: AsyncSession, tenant_id) -> dict:
    """Return connection status for the tenant's Telegram integration."""
    result = await db.execute(
        select(TenantIntegration).where(
            TenantIntegration.tenant_id == tenant_id,
            TenantIntegration.integration_type == "telegram",
        )
    )
    integration = result.scalar_one_or_none()
    if not integration or not integration.is_active:
        return {"connected": False, "chat_id": None, "username": None}

    config = integration.config or {}
    return {
        "connected": True,
        "chat_id": config.get("chat_id"),
        "username": config.get("username"),
    }


async def setup_webhook() -> dict:
    """Register the Telegram webhook. Raises ValueError if not configured."""
    if not settings.TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN no configurado")
    if not settings.TELEGRAM_WEBHOOK_URL:
        raise ValueError("TELEGRAM_WEBHOOK_URL no configurado")

    client = TelegramClient(settings.TELEGRAM_BOT_TOKEN)
    try:
        result = await client.set_webhook(
            url=settings.TELEGRAM_WEBHOOK_URL,
            secret_token=settings.TELEGRAM_WEBHOOK_SECRET or None,
        )
        return {"status": "webhook registrado", "result": result}
    finally:
        await client.close()
