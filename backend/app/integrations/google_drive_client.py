"""Google Drive API client using OAuth access tokens."""

import httpx

DRIVE_API = "https://www.googleapis.com/drive/v3"
UPLOAD_API = "https://www.googleapis.com/upload/drive/v3"


class GoogleDriveClient:
    """Wrapper around Google Drive REST API v3."""

    def __init__(self, access_token: str):
        self._client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=60,
        )

    async def close(self):
        await self._client.aclose()

    async def list_files(
        self,
        folder_id: str = "root",
        query: str = "",
        page_size: int = 50,
    ) -> list[dict]:
        """List files in a folder. Optional extra query filter."""
        q_parts = [f"'{folder_id}' in parents", "trashed = false"]
        if query:
            q_parts.append(query)
        params = {
            "q": " and ".join(q_parts),
            "pageSize": page_size,
            "fields": "files(id,name,mimeType,size,modifiedTime,webViewLink)",
            "orderBy": "modifiedTime desc",
        }
        resp = await self._client.get(f"{DRIVE_API}/files", params=params)
        resp.raise_for_status()
        return resp.json().get("files", [])

    async def get_file_metadata(self, file_id: str) -> dict:
        """Get metadata for a single file."""
        resp = await self._client.get(
            f"{DRIVE_API}/files/{file_id}",
            params={"fields": "id,name,mimeType,size,modifiedTime,webViewLink"},
        )
        resp.raise_for_status()
        return resp.json()

    async def download_file(self, file_id: str) -> bytes:
        """Download file content."""
        resp = await self._client.get(
            f"{DRIVE_API}/files/{file_id}",
            params={"alt": "media"},
        )
        resp.raise_for_status()
        return resp.content

    async def upload_file(
        self,
        name: str,
        content: bytes,
        mime_type: str = "application/octet-stream",
        folder_id: str = "root",
    ) -> dict:
        """Upload a file using simple upload."""
        metadata = {"name": name, "parents": [folder_id]}

        # Multipart upload
        import json

        boundary = "autoerp_boundary"
        body = (
            (
                f"--{boundary}\r\n"
                f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
                f"{json.dumps(metadata)}\r\n"
                f"--{boundary}\r\n"
                f"Content-Type: {mime_type}\r\n\r\n"
            ).encode("utf-8")
            + content
            + f"\r\n--{boundary}--".encode("utf-8")
        )

        resp = await self._client.post(
            f"{UPLOAD_API}/files?uploadType=multipart",
            content=body,
            headers={"Content-Type": f"multipart/related; boundary={boundary}"},
        )
        resp.raise_for_status()
        return resp.json()

    async def create_folder(self, name: str, parent_id: str = "root") -> dict:
        """Create a folder in Drive."""
        resp = await self._client.post(
            f"{DRIVE_API}/files",
            json={
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id],
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def sync_document(
        self, name: str, content: bytes, mime_type: str, folder_id: str = "root"
    ) -> dict:
        """Upload a document from the internal system to Drive."""
        return await self.upload_file(name, content, mime_type, folder_id)

    async def backup_invoice(
        self, invoice_name: str, pdf_bytes: bytes, folder_id: str = "root"
    ) -> dict:
        """Backup an invoice PDF to Drive."""
        return await self.upload_file(invoice_name, pdf_bytes, "application/pdf", folder_id)
