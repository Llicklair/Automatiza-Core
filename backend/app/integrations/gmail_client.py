"""Gmail API client using OAuth access tokens."""

import base64
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx

GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"


class GmailClient:
    """Wrapper around Gmail REST API v1."""

    def __init__(self, access_token: str):
        self._token = access_token
        self._client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        )

    async def close(self):
        await self._client.aclose()

    async def list_messages(self, query: str = "", max_results: int = 20) -> list[dict]:
        """List message summaries matching an optional query."""
        params = {"maxResults": max_results}
        if query:
            params["q"] = query
        resp = await self._client.get(f"{GMAIL_API}/messages", params=params)
        resp.raise_for_status()
        message_ids = resp.json().get("messages", [])

        messages = []
        for msg_ref in message_ids[:max_results]:
            detail = await self.get_message(msg_ref["id"])
            messages.append(detail)
        return messages

    async def get_message(self, message_id: str) -> dict:
        """Get a single message with headers and snippet."""
        resp = await self._client.get(
            f"{GMAIL_API}/messages/{message_id}",
            params={"format": "metadata", "metadataHeaders": ["From", "To", "Subject", "Date"]},
        )
        resp.raise_for_status()
        data = resp.json()
        headers = {h["name"]: h["value"] for h in data.get("payload", {}).get("headers", [])}
        return {
            "id": data["id"],
            "thread_id": data.get("threadId"),
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "snippet": data.get("snippet", ""),
            "label_ids": data.get("labelIds", []),
        }

    async def get_message_body(self, message_id: str) -> str:
        """Get the full body text of a message."""
        resp = await self._client.get(
            f"{GMAIL_API}/messages/{message_id}",
            params={"format": "full"},
        )
        resp.raise_for_status()
        data = resp.json()
        return _extract_body(data.get("payload", {}))

    async def send_message(
        self,
        to: str,
        subject: str,
        body: str,
        html: bool = False,
        attachments: list[tuple[str, bytes]] | None = None,
    ) -> dict:
        """Send an email. attachments = list of (filename, content_bytes)."""
        if attachments:
            msg = MIMEMultipart()
            msg.attach(MIMEText(body, "html" if html else "plain", "utf-8"))
            for fname, content in attachments:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(content)
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f'attachment; filename="{fname}"')
                msg.attach(part)
        else:
            msg = MIMEText(body, "html" if html else "plain", "utf-8")

        msg["To"] = to
        msg["Subject"] = subject

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
        resp = await self._client.post(
            f"{GMAIL_API}/messages/send",
            json={"raw": raw},
        )
        resp.raise_for_status()
        return resp.json()

    async def search_messages(self, query: str, max_results: int = 10) -> list[dict]:
        """Search messages using Gmail query syntax."""
        return await self.list_messages(query=query, max_results=max_results)


def _extract_body(payload: dict) -> str:
    """Recursively extract text body from Gmail payload."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        result = _extract_body(part)
        if result:
            return result
    return ""
