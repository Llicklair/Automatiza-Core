"""
Rutas de mensajería externa — Telegram webhook + gestión de conexión.

El webhook recibe mensajes de Telegram, busca el tenant vinculado al chat_id,
y enruta el mensaje al orquestador de agentes IA.
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.messaging import TelegramConnectResponse
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.integrations.telegram_client import TelegramClient
from app.middleware.rate_limit import limiter
from app.services import messaging_service as svc

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
