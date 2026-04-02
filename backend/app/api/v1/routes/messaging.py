"""
Rutas de mensajería externa — Telegram webhook + gestión de conexión.

El webhook recibe mensajes de Telegram, busca el tenant vinculado al chat_id,
y enruta el mensaje al orquestador de agentes IA.
"""
import logging
import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import TenantIntegration, User
from app.integrations.telegram_client import TelegramClient, TelegramUpdate
from app.middleware.rate_limit import limiter
from app.services.encryption import encrypt_credentials, decrypt_credentials

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/messaging", tags=["messaging"])


# ─── Telegram Webhook (sin auth — llamado por Telegram) ──────────────────────

@router.post("/telegram/webhook")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Recibe updates de Telegram Bot API.
    Verifica secret_token header, busca tenant por chat_id, invoca orquestador.
    """
    # Verificar secret token
    secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if settings.TELEGRAM_WEBHOOK_SECRET:
        if not TelegramClient.verify_secret(secret_header, settings.TELEGRAM_WEBHOOK_SECRET):
            logger.warning("Telegram webhook: secret token inválido")
            raise HTTPException(status_code=403, detail="Forbidden")

    body = await request.json()
    update = TelegramClient.parse_update(body)
    if not update:
        return {"ok": True}  # Ignorar updates sin texto (fotos, stickers, etc.)

    chat_id = update.chat_id
    text = update.text.strip()

    # ── Comando /start con token de vinculación ──
    if text.startswith("/start "):
        link_token = text.split(" ", 1)[1].strip()
        await _handle_link_command(db, chat_id, update.username, update.first_name, link_token)
        return {"ok": True}

    if text == "/start":
        await _send_reply(chat_id, (
            "¡Hola! Soy el asistente IA de tu empresa.\n\n"
            "Para vincular tu Telegram, ve a Configuración > Integraciones "
            "en el panel web y sigue las instrucciones."
        ))
        return {"ok": True}

    # ── Buscar tenant vinculado a este chat_id ──
    integration = await _find_integration_by_chat(db, chat_id)
    if not integration:
        await _send_reply(chat_id, (
            "No he encontrado ninguna empresa vinculada a este chat.\n"
            "Vincula tu cuenta desde el panel web: Configuración > Integraciones > Telegram."
        ))
        return {"ok": True}

    # ── Enviar typing + invocar orquestador ──
    tenant_id = str(integration.tenant_id)
    try:
        bot_token = settings.TELEGRAM_BOT_TOKEN
        client = TelegramClient(bot_token)
        await client.send_typing(chat_id)
        await client.close()
    except Exception:
        pass

    # Invocar orquestador en background
    import asyncio
    asyncio.create_task(_process_and_reply(tenant_id, chat_id, text, update.message_id))

    return {"ok": True}


async def _process_and_reply(tenant_id: str, chat_id: int, text: str, reply_to: int):
    """Crea una Task en BD, despacha al orquestador, espera resultado y responde por Telegram."""
    import asyncio
    from uuid import UUID as _UUID
    from sqlalchemy import select as _sel

    try:
        from app.db.base import AsyncSessionLocal
        from app.db.models.models import Task
        from app.services.task_dispatch import dispatch_orchestrator

        # 1. Crear tarea en BD (igual que POST /tasks)
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

        # 2. Despachar al orquestador
        await dispatch_orchestrator(task_id)

        # 3. Poll hasta que la tarea termine (max 120s)
        response_text = "Tu solicitud está siendo procesada."
        for _ in range(60):
            await asyncio.sleep(2)
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    _sel(Task).where(Task.id == _UUID(task_id))
                )
                task = result.scalar_one_or_none()
                if not task:
                    break
                if task.status in ("completed", "failed", "done"):
                    # Extraer respuesta de output o agent_results
                    output = task.output_data or {}
                    if isinstance(output, dict):
                        # Buscar respuesta en output.response o agent_results
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

        await _send_reply(chat_id, response_text, reply_to_message_id=reply_to)

    except Exception as e:
        logger.exception("Error procesando mensaje Telegram para tenant %s: %s", tenant_id, e)
        await _send_reply(chat_id, "Ha ocurrido un error procesando tu mensaje. Inténtalo de nuevo.")


async def _send_reply(chat_id: int, text: str, reply_to_message_id: int | None = None):
    """Envía respuesta por Telegram usando el bot del sistema."""
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


async def _handle_link_command(
    db: AsyncSession, chat_id: int, username: str | None, first_name: str | None, link_token: str,
):
    """Vincula un chat de Telegram con un tenant usando el token de vinculación."""
    # Buscar integración pendiente con ese link_token
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
            # Vincular
            creds["chat_id"] = chat_id
            creds["username"] = username or ""
            creds["first_name"] = first_name or ""
            creds.pop("link_token", None)
            integration.encrypted_credentials = encrypt_credentials(creds)
            integration.is_active = True
            integration.config = {"chat_id": chat_id, "username": username or ""}
            await db.commit()

            await _send_reply(chat_id, (
                f"¡Vinculación exitosa! 🎉\n\n"
                f"Este chat está ahora conectado a tu empresa.\n"
                f"Puedes escribirme cualquier cosa: crear facturas, consultar datos, "
                f"gestionar empleados, etc.\n\n"
                f"Escribe tu primera solicitud para empezar."
            ))
            return

    await _send_reply(chat_id, "Token de vinculación inválido o expirado. Genera uno nuevo desde el panel web.")


async def _find_integration_by_chat(db: AsyncSession, chat_id: int) -> TenantIntegration | None:
    """Busca la integración de Telegram activa para un chat_id."""
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


# ─── Gestión de conexión Telegram (requiere auth) ────────────────────────────

class TelegramConnectResponse(BaseModel):
    link_url: str
    link_token: str
    bot_username: str | None = None


@limiter.limit("10/minute")
@router.post("/telegram/connect", response_model=TelegramConnectResponse)
async def connect_telegram(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Genera un token de vinculación para conectar Telegram con el tenant.
    El usuario debe abrir el link en Telegram para completar la vinculación.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=400, detail="Telegram no está configurado en el servidor")

    link_token = secrets.token_urlsafe(32)

    # Obtener username del bot
    bot_username = None
    client = TelegramClient(settings.TELEGRAM_BOT_TOKEN)
    try:
        me = await client.get_me()
        bot_username = me.get("result", {}).get("username")
    except Exception as e:
        logger.warning("No se pudo obtener info del bot: %s", e)
    finally:
        await client.close()

    # Upsert integration (inactiva hasta que el usuario haga /start)
    result = await db.execute(
        select(TenantIntegration).where(
            TenantIntegration.tenant_id == current_user.tenant_id,
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
        db.add(TenantIntegration(
            tenant_id=current_user.tenant_id,
            integration_type="telegram",
            encrypted_credentials=encrypted,
            is_active=False,
            config={},
        ))

    await db.commit()

    link_url = f"https://t.me/{bot_username}?start={link_token}" if bot_username else ""

    return TelegramConnectResponse(
        link_url=link_url,
        link_token=link_token,
        bot_username=bot_username,
    )


@limiter.limit("10/minute")
@router.delete("/telegram/disconnect")
async def disconnect_telegram(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Desvincula Telegram del tenant."""
    result = await db.execute(
        select(TenantIntegration).where(
            TenantIntegration.tenant_id == current_user.tenant_id,
            TenantIntegration.integration_type == "telegram",
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integración de Telegram no encontrada")

    # Notificar al usuario en Telegram antes de desconectar
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


@limiter.limit("10/minute")
@router.get("/telegram/status")
async def telegram_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve el estado de la integración Telegram del tenant."""
    result = await db.execute(
        select(TenantIntegration).where(
            TenantIntegration.tenant_id == current_user.tenant_id,
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


# ─── Setup webhook (llamar una vez al desplegar) ─────────────────────────────

@limiter.limit("3/minute")
@router.post("/telegram/setup-webhook")
async def setup_telegram_webhook(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Registra el webhook de Telegram. Solo necesita llamarse una vez.
    Requiere TELEGRAM_BOT_TOKEN y TELEGRAM_WEBHOOK_URL en .env.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=400, detail="TELEGRAM_BOT_TOKEN no configurado")
    if not settings.TELEGRAM_WEBHOOK_URL:
        raise HTTPException(status_code=400, detail="TELEGRAM_WEBHOOK_URL no configurado")

    client = TelegramClient(settings.TELEGRAM_BOT_TOKEN)
    try:
        result = await client.set_webhook(
            url=settings.TELEGRAM_WEBHOOK_URL,
            secret_token=settings.TELEGRAM_WEBHOOK_SECRET or None,
        )
        return {"status": "webhook registrado", "result": result}
    finally:
        await client.close()
