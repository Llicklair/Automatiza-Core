"""
Telegram Bot API client — enviar mensajes, gestionar webhook, parsear updates.

Cada tenant puede vincular su chat de Telegram al ERP.
Los mensajes entrantes se enrutan al orquestador de agentes.
"""
import hashlib
import hmac
import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.telegram.org/bot{token}"


@dataclass
class TelegramUpdate:
    """Parsed Telegram update (solo lo que necesitamos)."""
    update_id: int
    chat_id: int
    username: str | None
    first_name: str | None
    text: str
    message_id: int


class TelegramClient:
    """Async client for Telegram Bot API."""

    def __init__(self, bot_token: str):
        self._token = bot_token
        self._base = BASE_URL.format(token=bot_token)
        self._http = httpx.AsyncClient(timeout=30)

    async def close(self):
        await self._http.aclose()

    # ─── Enviar mensajes ──────────────────────────────────────────────────

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "HTML",
        reply_to_message_id: int | None = None,
    ) -> dict:
        """Envía un mensaje de texto. Trocea si >4096 chars."""
        results = []
        # Telegram limit: 4096 chars per message
        chunks = [text[i:i + 4096] for i in range(0, len(text), 4096)]
        for chunk in chunks:
            payload = {
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": parse_mode,
            }
            if reply_to_message_id and not results:
                payload["reply_to_message_id"] = reply_to_message_id
            resp = await self._http.post(f"{self._base}/sendMessage", json=payload)
            resp.raise_for_status()
            results.append(resp.json())
        return results[-1] if results else {}

    async def send_typing(self, chat_id: int) -> None:
        """Envía indicador de 'escribiendo...' al chat."""
        try:
            await self._http.post(
                f"{self._base}/sendChatAction",
                json={"chat_id": chat_id, "action": "typing"},
            )
        except Exception:
            pass  # Non-critical

    # ─── Webhook management ───────────────────────────────────────────────

    async def set_webhook(self, url: str, secret_token: str | None = None) -> dict:
        """Registra la URL de webhook en Telegram."""
        payload = {"url": url, "allowed_updates": ["message"]}
        if secret_token:
            payload["secret_token"] = secret_token
        resp = await self._http.post(f"{self._base}/setWebhook", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def delete_webhook(self) -> dict:
        resp = await self._http.post(f"{self._base}/deleteWebhook")
        resp.raise_for_status()
        return resp.json()

    async def get_webhook_info(self) -> dict:
        resp = await self._http.get(f"{self._base}/getWebhookInfo")
        resp.raise_for_status()
        return resp.json()

    async def get_me(self) -> dict:
        """Verifica que el token es válido devolviendo info del bot."""
        resp = await self._http.get(f"{self._base}/getMe")
        resp.raise_for_status()
        return resp.json()

    # ─── Parseo de updates ────────────────────────────────────────────────

    @staticmethod
    def parse_update(data: dict) -> TelegramUpdate | None:
        """Extrae los campos útiles de un Telegram Update JSON."""
        msg = data.get("message")
        if not msg:
            return None
        text = msg.get("text", "")
        if not text:
            return None
        chat = msg.get("chat", {})
        from_user = msg.get("from", {})
        return TelegramUpdate(
            update_id=data.get("update_id", 0),
            chat_id=chat.get("id", 0),
            username=from_user.get("username"),
            first_name=from_user.get("first_name"),
            text=text,
            message_id=msg.get("message_id", 0),
        )

    @staticmethod
    def verify_secret(header_token: str | None, expected_secret: str) -> bool:
        """Verifica el header X-Telegram-Bot-Api-Secret-Token."""
        if not header_token or not expected_secret:
            return False
        return hmac.compare_digest(header_token, expected_secret)
