"""
Rutas de mensajería externa — Telegram webhook + Email + gestión de conexión.
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.messaging import TelegramConnectResponse
from app.core.dependencies import get_current_user
from app.core.tenant_context import rls_bypass, set_current_tenant
from app.db.base import get_db
from app.db.models.models import User
from app.integrations.telegram_client import TelegramClient
from app.middleware.rate_limit import limiter
from app.services.integration import messaging as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/messaging", tags=["messaging"])

# Retiene referencias a tasks fire-and-forget para que el GC de CPython no las
# recolecte a media ejecución (ver asyncio docs sobre create_task).
_background_tasks: set = set()


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
        # SEC.RLS: resolución del token de vinculación → tenant es pre-tenant
        # (el webhook no tiene JWT ni tenant en contexto todavía).
        with rls_bypass():
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
    # SEC.RLS: la resolución chat_id → tenant es pre-tenant (webhook sin JWT);
    # debe ir en bypass. Una vez conocido, fijamos el tenant para el resto.
    with rls_bypass():
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
    # SEC.RLS: tenant ya resuelto → scope correcto para el resto del handler.
    set_current_tenant(tenant_id)
    await svc.send_typing_indicator(chat_id)

    _task = asyncio.create_task(
        svc.process_and_reply(tenant_id, chat_id, text, update.message_id)
    )
    _background_tasks.add(_task)
    _task.add_done_callback(_background_tasks.discard)

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
    from app.services.email.sender import send_email as send_email_service

    result = await send_email_service(
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
    from app.agents.email import run_email_agent

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
    from app.services.email.credentials import get_email_credentials, get_oauth_token

    tenant_id = str(current_user.tenant_id)
    gmail = bool(await get_oauth_token(tenant_id, "gmail"))
    outlook = bool(await get_oauth_token(tenant_id, "outlook"))
    smtp = bool(await get_email_credentials(tenant_id))
    configured = gmail or outlook or smtp
    return {
        "configured": configured,
        "providers": {
            "gmail": gmail,
            "outlook": outlook,
            "smtp": smtp,
        },
    }


@limiter.limit("30/minute")
@router.get("/email/inbox")
async def email_inbox(
    request: Request,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
):
    """
    Lista los últimos mensajes recibidos del proveedor configurado.
    Detecta provider en este orden: gmail > outlook. Devuelve formato uniforme.
    """
    from app.services.email.credentials import get_oauth_token

    tenant_id = str(current_user.tenant_id)
    limit = max(1, min(limit, 50))

    gmail_token = await get_oauth_token(tenant_id, "gmail")
    if gmail_token:
        from app.integrations.gmail_client import GmailClient

        client = GmailClient(gmail_token)
        try:
            msgs = await client.list_messages(max_results=limit)
            return {
                "provider": "gmail",
                "messages": [
                    {
                        "id": m["id"],
                        "from": m.get("from", ""),
                        "subject": m.get("subject", ""),
                        "date": m.get("date", ""),
                        "snippet": m.get("snippet", ""),
                        "unread": "UNREAD" in (m.get("label_ids") or []),
                    }
                    for m in msgs
                ],
            }
        finally:
            await client.close()

    outlook_token = await get_oauth_token(tenant_id, "outlook")
    if outlook_token:
        from app.integrations.outlook_client import OutlookClient

        client = OutlookClient(outlook_token)
        try:
            msgs = await client.list_messages(top=limit)
            return {
                "provider": "outlook",
                "messages": [
                    {
                        "id": m["id"],
                        "from": m.get("from", ""),
                        "subject": m.get("subject", ""),
                        "date": m.get("date", ""),
                        "snippet": m.get("snippet", ""),
                        "unread": not m.get("is_read", False),
                    }
                    for m in msgs
                ],
            }
        finally:
            await client.close()

    return {"provider": None, "messages": []}


@limiter.limit("30/minute")
@router.get("/drive/files")
async def drive_list_files(
    request: Request,
    folder: str = "root",
    q: str = "",
    current_user: User = Depends(get_current_user),
):
    """Lista archivos de Google Drive del tenant. Requiere OAuth Gmail con scope drive."""
    from app.services.email.credentials import get_oauth_token

    tenant_id = str(current_user.tenant_id)
    token = await get_oauth_token(tenant_id, "gmail")
    if not token:
        raise HTTPException(status_code=400, detail="Conecta Google (Gmail) para acceder a Drive")

    from app.integrations.google_drive_client import GoogleDriveClient

    client = GoogleDriveClient(token)
    try:
        # Mapear consulta libre del usuario a query Drive
        query_filter = f"name contains '{q}'" if q else ""
        files = await client.list_files(folder_id=folder, query=query_filter, page_size=50)
        return {
            "files": [
                {
                    "id": f.get("id", ""),
                    "name": f.get("name", ""),
                    "mime_type": f.get("mimeType", ""),
                    "size": int(f["size"]) if f.get("size") else None,
                    "modified": f.get("modifiedTime", ""),
                    "is_folder": f.get("mimeType") == "application/vnd.google-apps.folder",
                }
                for f in files
            ],
        }
    finally:
        await client.close()


@limiter.limit("20/minute")
@router.post("/drive/attach/{file_id}")
async def drive_attach_as_document(
    request: Request,
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Descarga un fichero de Drive y lo guarda como Document del tenant.
    Devuelve el Document para que el frontend lo añada como adjunto al correo.
    """
    from app.services.email.credentials import get_oauth_token

    tenant_id = str(current_user.tenant_id)
    token = await get_oauth_token(tenant_id, "gmail")
    if not token:
        raise HTTPException(status_code=400, detail="Conecta Google (Gmail) para acceder a Drive")

    from app.integrations.google_drive_client import GoogleDriveClient

    client = GoogleDriveClient(token)
    try:
        meta = await client.get_file_metadata(file_id)
        if meta.get("mimeType") == "application/vnd.google-apps.folder":
            raise HTTPException(status_code=400, detail="No se puede adjuntar una carpeta")
        content = await client.download_file(file_id)
    finally:
        await client.close()

    from app.services.documents import service as docs_svc

    doc = await docs_svc.upload_single(
        meta.get("name") or "drive-file",
        content,
        meta.get("mimeType"),
        current_user.tenant_id,
        current_user.id,
        db,
        "email-attachment",
    )
    return {
        "id": str(doc.id),
        "file_name": doc.file_name,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "status": doc.status,
        "category": doc.category,
        "parsed_content": doc.parsed_content,
        "created_at": doc.created_at.isoformat() if doc.created_at else "",
        "processed_at": doc.processed_at.isoformat() if doc.processed_at else None,
        "task_id": str(doc.task_id) if doc.task_id else None,
    }


@limiter.limit("60/minute")
@router.get("/email/messages/{message_id}")
async def email_message_detail(
    request: Request,
    message_id: str,
    current_user: User = Depends(get_current_user),
):
    """Devuelve el cuerpo completo de un mensaje del proveedor configurado."""
    from app.services.email.credentials import get_oauth_token

    tenant_id = str(current_user.tenant_id)

    gmail_token = await get_oauth_token(tenant_id, "gmail")
    if gmail_token:
        from app.integrations.gmail_client import GmailClient

        client = GmailClient(gmail_token)
        try:
            meta = await client.get_message(message_id)
            body = await client.get_message_body(message_id)
            return {
                "provider": "gmail",
                "id": meta["id"],
                "from": meta.get("from", ""),
                "to": meta.get("to", ""),
                "subject": meta.get("subject", ""),
                "date": meta.get("date", ""),
                "body": body,
            }
        finally:
            await client.close()

    outlook_token = await get_oauth_token(tenant_id, "outlook")
    if outlook_token:
        from app.integrations.outlook_client import OutlookClient

        client = OutlookClient(outlook_token)
        try:
            m = await client.get_message(message_id)
            return {
                "provider": "outlook",
                "id": m.get("id", ""),
                "from": m.get("from", ""),
                "to": m.get("to", ""),
                "subject": m.get("subject", ""),
                "date": m.get("date", ""),
                "body": m.get("body", ""),
            }
        finally:
            await client.close()

    raise HTTPException(status_code=400, detail="No hay proveedor de email configurado")


# ─── IA: clasificación de bandeja + redacción de borradores ───────────────────


class _ClassifyMessageIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    # "from" es palabra reservada en Python → usar alias
    from_: str = Field(default="", alias="from")
    subject: str = ""
    snippet: str = ""


class _ClassifyRequest(BaseModel):
    messages: list[_ClassifyMessageIn]


@router.post("/email/classify")
@limiter.limit("10/minute")
async def classify_email_inbox(
    request: Request,
    payload: _ClassifyRequest,
    current_user: User = Depends(get_current_user),
):
    """Clasifica una lista de emails (urgencia, categoría, requiere respuesta)."""
    from app.services.email_ai import EmailAIError, classify_messages

    try:
        results = await classify_messages([
            {"id": m.id, "from": m.from_, "subject": m.subject, "snippet": m.snippet}
            for m in payload.messages
        ])
    except EmailAIError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        logger.exception("Error clasificando bandeja")
        raise HTTPException(status_code=500, detail="Error interno al clasificar mensajes")

    return {"items": [r.to_dict() for r in results]}


class _DraftRequest(BaseModel):
    message_id: str
    context: str | None = None


@router.post("/email/draft-reply")
@limiter.limit("20/minute")
async def draft_email_reply(
    request: Request,
    payload: _DraftRequest,
    current_user: User = Depends(get_current_user),
):
    """Redacta un borrador de respuesta para el mensaje con id dado.

    Reusa el handler de /email/messages/{id} para obtener el cuerpo completo
    y pasa el contexto opcional a la IA.
    """
    from app.services.email.credentials import get_oauth_token
    from app.services.email_ai import EmailAIError, draft_reply

    tenant_id = str(current_user.tenant_id)

    full_msg: dict | None = None
    for provider, ClientCls in [("gmail", "GmailClient"), ("outlook", "OutlookClient")]:
        token = await get_oauth_token(tenant_id, provider)
        if not token:
            continue
        if provider == "gmail":
            from app.integrations.gmail_client import GmailClient
            client = GmailClient(token)
        else:
            from app.integrations.outlook_client import OutlookClient
            client = OutlookClient(token)
        try:
            full_msg = await client.get_message(payload.message_id)
        except Exception:
            full_msg = None
        finally:
            await client.close()
        if full_msg:
            break

    if not full_msg:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado o sin proveedor de email")

    try:
        draft = await draft_reply(
            full_msg,
            context=payload.context or "",
            user_full_name=getattr(current_user, "full_name", None),
        )
    except EmailAIError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        logger.exception("Error redactando borrador")
        raise HTTPException(status_code=500, detail="Error interno al generar el borrador")

    return draft.to_dict()
