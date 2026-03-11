"""Outlook / Microsoft Graph Mail client using OAuth access tokens."""

import base64

import httpx

GRAPH_API = "https://graph.microsoft.com/v1.0"


class OutlookClient:
    """Wrapper around Microsoft Graph Mail API."""

    def __init__(self, access_token: str):
        self._token = access_token
        self._client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        )

    async def close(self):
        await self._client.aclose()

    async def list_messages(self, folder: str = "inbox", top: int = 20, search: str = "") -> list[dict]:
        """List messages from a mail folder."""
        params: dict = {
            "$top": top,
            "$select": "id,subject,from,toRecipients,receivedDateTime,bodyPreview,isRead",
            "$orderby": "receivedDateTime desc",
        }
        if search:
            params["$search"] = f'"{search}"'
        resp = await self._client.get(f"{GRAPH_API}/me/mailFolders/{folder}/messages", params=params)
        resp.raise_for_status()
        return [_normalize_message(m) for m in resp.json().get("value", [])]

    async def get_message(self, message_id: str) -> dict:
        """Get a single message with body."""
        resp = await self._client.get(
            f"{GRAPH_API}/me/messages/{message_id}",
            params={"$select": "id,subject,from,toRecipients,receivedDateTime,body,isRead"},
        )
        resp.raise_for_status()
        return _normalize_message(resp.json())

    async def send_message(
        self, to: str, subject: str, body: str, html: bool = False,
        attachments: list[tuple[str, bytes]] | None = None,
    ) -> dict:
        """Send an email via Microsoft Graph."""
        message_payload: dict = {
            "subject": subject,
            "body": {
                "contentType": "HTML" if html else "Text",
                "content": body,
            },
            "toRecipients": [{"emailAddress": {"address": to}}],
        }
        if attachments:
            message_payload["attachments"] = [
                {
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": fname,
                    "contentBytes": base64.b64encode(content).decode("ascii"),
                }
                for fname, content in attachments
            ]

        resp = await self._client.post(
            f"{GRAPH_API}/me/sendMail",
            json={"message": message_payload, "saveToSentItems": True},
        )
        resp.raise_for_status()
        return {"status": "sent"}

    async def search_messages(self, query: str, top: int = 10) -> list[dict]:
        """Search messages across all folders."""
        params = {
            "$search": f'"{query}"',
            "$top": top,
            "$select": "id,subject,from,toRecipients,receivedDateTime,bodyPreview,isRead",
        }
        resp = await self._client.get(f"{GRAPH_API}/me/messages", params=params)
        resp.raise_for_status()
        return [_normalize_message(m) for m in resp.json().get("value", [])]


def _normalize_message(m: dict) -> dict:
    """Normalize Graph API message to a common format."""
    from_addr = m.get("from", {}).get("emailAddress", {})
    to_list = m.get("toRecipients", [])
    return {
        "id": m.get("id", ""),
        "subject": m.get("subject", ""),
        "from": from_addr.get("address", ""),
        "from_name": from_addr.get("name", ""),
        "to": ", ".join(r.get("emailAddress", {}).get("address", "") for r in to_list),
        "date": m.get("receivedDateTime", ""),
        "snippet": m.get("bodyPreview", ""),
        "body": m.get("body", {}).get("content", ""),
        "is_read": m.get("isRead", False),
    }
