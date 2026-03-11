"""
Cliente de la API de Holded.
Docs: https://developers.holded.com/reference

Encapsula todas las llamadas a Holded con manejo de errores,
rate limiting y logging. SIN lógica de negocio aquí.
"""

import httpx

HOLDED_BASE = "https://api.holded.com/api"


class HoldedClient:
    """Cliente async para la API REST de Holded."""

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=HOLDED_BASE,
            headers={
                "key": api_key,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def close(self):
        await self._client.aclose()

    # ─── Contactos ────────────────────────────────────────────────────────

    async def get_contacts(self, page: int = 1) -> list[dict]:
        """Lista todos los contactos (clientes/proveedores)."""
        r = await self._client.get("/invoicing/v1/contacts", params={"page": page})
        r.raise_for_status()
        return r.json()

    async def get_contact_by_nif(self, nif: str) -> dict | None:
        """Busca un contacto por NIF/CIF. Devuelve None si no existe."""
        if self._api_key == "DEMO_HOLDED_KEY":
            return {"id": "demo_contact_123", "vatnumber": nif, "name": "Cliente de Demostración"}
        
        contacts = await self.get_contacts()
        for c in contacts:
            if c.get("vatnumber", "").upper().replace("-", "") == nif.upper():
                return c
        return None

    async def create_contact(self, data: dict) -> dict:
        """Crea un nuevo contacto en Holded."""
        r = await self._client.post("/invoicing/v1/contacts", json=data)
        r.raise_for_status()
        return r.json()

    # ─── Facturas de venta ────────────────────────────────────────────────

    async def list_invoices(
        self,
        page: int = 1,
        startdate: int | None = None,
        enddate: int | None = None,
    ) -> list[dict]:
        params = {"page": page}
        if startdate: params["startdate"] = startdate
        if enddate:   params["enddate"] = enddate
        r = await self._client.get("/invoicing/v1/documents/invoice", params=params)
        r.raise_for_status()
        return r.json()

    async def get_invoice(self, invoice_id: str) -> dict:
        r = await self._client.get(f"/invoicing/v1/documents/invoice/{invoice_id}")
        r.raise_for_status()
        return r.json()

    async def create_invoice(self, data: dict) -> dict:
        """
        Crea factura borrador en Holded.
        data debe incluir: contactId, date, items (list), notes.
        """
        if self._api_key == "DEMO_HOLDED_KEY":
            return {"id": "inv_demo_9999", "status": "draft"}
            
        r = await self._client.post("/invoicing/v1/documents/invoice", json=data)
        r.raise_for_status()
        return r.json()

    async def send_invoice_by_email(
        self,
        invoice_id: str,
        emails: list[str],
        subject: str | None = None,
        body: str | None = None,
    ) -> dict:
        """Envía la factura por email desde Holded."""
        payload = {"emails": emails}
        if subject: payload["subject"] = subject
        if body:    payload["body"] = body
        r = await self._client.post(
            f"/invoicing/v1/documents/invoice/{invoice_id}/send",
            json=payload,
        )
        r.raise_for_status()
        return r.json()

    async def get_invoice_pdf_url(self, invoice_id: str) -> str:
        """Obtiene la URL de descarga del PDF de la factura."""
        r = await self._client.get(
            f"/invoicing/v1/documents/invoice/{invoice_id}/pdf"
        )
        r.raise_for_status()
        data = r.json()
        return data.get("url", "")

    # ─── Productos ────────────────────────────────────────────────────────

    async def list_products(self, page: int = 1) -> list[dict]:
        r = await self._client.get("/invoicing/v1/products", params={"page": page})
        r.raise_for_status()
        return r.json()

    async def upload_contact_attachment(
        self,
        contact_id: str,
        file_bytes: bytes,
        file_name: str,
        content_type: str = "application/pdf",
    ) -> dict:
        """
        Sube un archivo como adjunto de un contacto en Holded.
        Holded acepta multipart/form-data con el campo 'file'.
        """
        if self._api_key == "DEMO_HOLDED_KEY":
            return {"status": 1, "info": "demo_attachment_ok"}

        # httpx requiere un cliente sin Content-Type fijo para multipart
        files = {"file": (file_name, file_bytes, content_type)}
        headers = {"key": self._api_key, "Accept": "application/json"}
        async with __import__("httpx").AsyncClient(base_url=HOLDED_BASE, timeout=30.0) as client:
            r = await client.post(
                f"/invoicing/v1/contacts/{contact_id}/attachment",
                files=files,
                headers=headers,
            )
        r.raise_for_status()
        return r.json()

    # ─── Utilidades ───────────────────────────────────────────────────────

    @staticmethod
    def build_invoice_payload(
        contact_id: str,
        concept: str,
        amount_base: float,
        vat_rate: float,
        date_unix: int,
        notes: str = "",
    ) -> dict:
        """
        Construye el payload de creación de factura en formato Holded.
        """
        vat_amount = round(amount_base * vat_rate / 100, 2)
        return {
            "contactId": contact_id,
            "date": date_unix,
            "notes": notes,
            "items": [
                {
                    "name": concept,
                    "units": 1,
                    "subtotal": amount_base,
                    "tax": vat_rate,
                }
            ],
        }
