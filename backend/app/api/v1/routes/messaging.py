"""
Rutas de mensajería externa — Telegram webhook + Email + gestión de conexión.
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.messaging import TelegramConnectResponse
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.integrations.telegram_client import TelegramClient
from app.middleware.rate_limit import limiter
from app.services.integration import messaging as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/messaging", tags=["messaging"])


# ─── Telegram Webhook (sin auth — llamado por Telegram) ──────────────────────


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Recibe updates de Telegram Bot API.
    Verifica secret_token header, busca tenant por chat_id, invoca orquestador.
    """
    secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if not svc.verify_webhook_secret(secret_header):
        logger.warning("Telegram webhook: secret token inválido")
        raise HTTPException(status_code=403, detail="Forbidden")

    body = await request.json()
    update = TelegramClient.parse_update(body)
    if not update:
        return {"ok": True}

    chat_id = update.chat_id
    text = update.text.strip()

    # ── Comando /start con token de vinculación ──
    if text.startswith("/start "):
        link_token = text.split(" ", 1)[1].strip()
        await svc.handle_link_command(db, chat_id, update.username, update.first_name, link_token)
        return {"ok": True}

    if text == "/start":
        await svc.send_reply(
            chat_id,
            (
                "¡Hola! Soy el asistente IA de tu empresa.\n\n"
                "Para vincular tu Telegram, ve a Configuración > Integraciones "
                "en el panel web y sigue las instrucciones."
            ),
        )
        return {"ok": True}

    # ── Buscar tenant vinculado a este chat_id ──
    integration = await svc.find_integration_by_chat(db, chat_id)
    if not integration:
        await svc.send_reply(
            chat_id,
            (
                "No he encontrado ninguna empresa vinculada a este chat.\n"
                "Vincula tu cuenta desde el panel web: Configuración > Integraciones > Telegram."
            ),
        )
        return {"ok": True}

    # ── Enviar typing + invocar orquestador ──
    tenant_id = str(integration.tenant_id)
    await svc.send_typing_indicator(chat_id)

    asyncio.create_task(svc.process_and_reply(tenant_id, chat_id, text, update.message_id))

    return {"ok": True}


# ─── Gestión de conexión Telegram (requiere auth) ────────────────────────────


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
    try:
        result = await svc.connect_telegram(db, current_user.tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return TelegramConnectResponse(**result)


@limiter.limit("10/minute")
@router.delete("/telegram/disconnect")
async def disconnect_telegram(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Desvincula Telegram del tenant."""
    try:
        return await svc.disconnect_telegram(db, current_user.tenant_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@limiter.limit("10/minute")
@router.get("/telegram/status")
async def telegram_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve el estado de la integración Telegram del tenant."""
    return await svc.get_telegram_status(db, current_user.tenant_id)


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
    try:
        return await svc.setup_webhook()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Email ───────────────────────────────────────────────────────────────────


class EmailSendPayload(BaseModel):
    to: EmailStr
    subject: str
    body: str
    attachment_ids: list[str] | None = None


class EmailInstructPayload(BaseModel):
    message: str
    task_id: str | None = None


@limiter.limit("30/minute")
@router.post("/email/send")
async def send_email(
    request: Request,
    payload: EmailSendPayload,
    current_user: User = Depends(get_current_user),
):
    """Envía un email usando las credenciales del tenant (Gmail > Outlook > SMTP)."""
    from app.agents.email.agent import send_email_direct

    result = await send_email_direct(
        tenant_id=str(current_user.tenant_id),
        to=payload.to,
        subject=payload.subject,
        body=payload.body,
        attachment_ids=payload.attachment_ids,
    )
    return {"result": result}


@limiter.limit("20/minute")
@router.post("/email/instruct")
async def instruct_email_agent(
    request: Request,
    payload: EmailInstructPayload,
    current_user: User = Depends(get_current_user),
):
    """Ejecuta el email agent con una instrucción en lenguaje natural."""
    from app.agents.email.agent import run_email_agent

    result = await run_email_agent(
        user_intent=payload.message,
        tenant_id=str(current_user.tenant_id),
        task_id=payload.task_id,
    )
    return {
        "success": result.success,
        "action": result.action,
        "messages": result.extracted_data.get("messages_processed", []),
        "error": result.error,
    }


@router.get("/email/status")
async def email_status(
    current_user: User = Depends(get_current_user),
):
    """Devuelve qué proveedores de email están configurados para el tenant."""
    from app.agents.email.tools import _get_email_credentials, _get_oauth_token

    tenant_id = str(current_user.tenant_id)
    gmail = bool(await _get_oauth_token(tenant_id, "gmail"))
    outlook = bool(await _get_oauth_token(tenant_id, "outlook"))
    smtp = bool(await _get_email_credentials(tenant_id))
    configured = gmail or outlook or smtp
    return {
        "configured": configured,
        "providers": {
            "gmail": gmail,
            "outlook": outlook,
            "smtp": smtp,
        },
    }
