"""OneDrive / Microsoft Graph Files client using OAuth access tokens."""

import httpx

GRAPH_API = "https://graph.microsoft.com/v1.0"


class OneDriveClient:
    """Wrapper around Microsoft Graph Drive API."""

    def __init__(self, access_token: str):
        self._client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=60,
        )

    async def close(self):
        await self._client.aclose()

    async def list_files(self, folder_path: str = "root", top: int = 50) -> list[dict]:
        """List files in a folder (use 'root' for root folder)."""
        if folder_path == "root":
            url = f"{GRAPH_API}/me/drive/root/children"
        else:
            url = f"{GRAPH_API}/me/drive/root:/{folder_path}:/children"

        params = {
            "$top": top,
            "$select": "id,name,size,lastModifiedDateTime,webUrl,file,folder",
            "$orderby": "lastModifiedDateTime desc",
        }
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()
        items = resp.json().get("value", [])
        return [
            {
                "id": i["id"],
                "name": i["name"],
                "size": i.get("size"),
                "lastModifiedDateTime": i.get("lastModifiedDateTime"),
                "webUrl": i.get("webUrl"),
                "mimeType": i.get("file", {}).get("mimeType"),
            }
            for i in items
        ]

    async def download_file(self, item_id: str) -> bytes:
        """Download file content by item ID."""
        resp = await self._client.get(f"{GRAPH_API}/me/drive/items/{item_id}/content")
        if resp.status_code in (301, 302):
            resp = await self._client.get(resp.headers["Location"])
        resp.raise_for_status()
        return resp.content

    async def upload_file(
        self, name: str, content: bytes, folder_path: str = "root",
    ) -> dict:
        """Upload a file (< 4MB) using simple upload."""
        if folder_path == "root":
            url = f"{GRAPH_API}/me/drive/root:/{name}:/content"
        else:
            url = f"{GRAPH_API}/me/drive/root:/{folder_path}/{name}:/content"

        resp = await self._client.put(
            url,
            content=content,
            headers={"Content-Type": "application/octet-stream"},
        )
        resp.raise_for_status()
        return resp.json()

    async def create_folder(self, name: str, parent_path: str = "root") -> dict:
        """Create a folder."""
        if parent_path == "root":
            url = f"{GRAPH_API}/me/drive/root/children"
        else:
            url = f"{GRAPH_API}/me/drive/root:/{parent_path}:/children"

        resp = await self._client.post(
            url,
            json={
                "name": name,
                "folder": {},
                "@microsoft.graph.conflictBehavior": "rename",
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def sync_document(self, name: str, content: bytes, folder_path: str = "root") -> dict:
        """Upload a document from the internal system to OneDrive."""
        return await self.upload_file(name, content, folder_path)

    async def backup_invoice(self, invoice_name: str, pdf_bytes: bytes, folder_path: str = "root") -> dict:
        """Backup an invoice PDF to OneDrive."""
        return await self.upload_file(invoice_name, pdf_bytes, folder_path)
