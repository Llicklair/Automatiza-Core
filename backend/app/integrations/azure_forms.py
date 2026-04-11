"""
Cliente de Azure Form Recognizer (Document Intelligence).
Extrae datos estructurados de facturas, contratos y documentos en general.
Docs: https://learn.microsoft.com/azure/ai-services/document-intelligence/
"""

import asyncio

import httpx


class AzureFormsClient:
    """
    Cliente async para Azure Document Intelligence.
    Modelo prebuilt-invoice: extrae importe, proveedor, fecha, NIF, líneas de factura.
    Modelo prebuilt-document: extrae entidades genéricas de cualquier documento.
    """

    def __init__(self, endpoint: str, api_key: str):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self._client = httpx.AsyncClient(
            headers={"Ocp-Apim-Subscription-Key": api_key},
            timeout=60.0,
        )

    async def close(self):
        await self._client.aclose()

    # ─── Facturas ─────────────────────────────────────────────────────────

    async def analyze_invoice(
        self, file_bytes: bytes, content_type: str = "application/pdf"
    ) -> dict:
        """
        Analiza una factura recibida (PDF o imagen) y devuelve datos estructurados.
        Usa el modelo prebuilt-invoice de Azure.
        """
        url = f"{self.endpoint}/documentintelligence/documentModels/prebuilt-invoice:analyze"
        params = {"api-version": "2024-02-29-preview", "outputContentFormat": "markdown"}

        # Subir documento
        resp = await self._client.post(
            url,
            params=params,
            content=file_bytes,
            headers={"Content-Type": content_type, "Ocp-Apim-Subscription-Key": self.api_key},
        )
        resp.raise_for_status()

        # Obtener URL de resultado (operación asíncrona de Azure)
        operation_url = resp.headers.get("Operation-Location")
        if not operation_url:
            raise ValueError("Azure no devolvió Operation-Location en la respuesta")

        return await self._poll_result(operation_url)

    async def analyze_document(
        self, file_bytes: bytes, content_type: str = "application/pdf"
    ) -> dict:
        """Analiza un documento genérico (contrato, extracto...)."""
        url = f"{self.endpoint}/documentintelligence/documentModels/prebuilt-document:analyze"
        params = {"api-version": "2024-02-29-preview"}

        resp = await self._client.post(
            url,
            params=params,
            content=file_bytes,
            headers={"Content-Type": content_type, "Ocp-Apim-Subscription-Key": self.api_key},
        )
        resp.raise_for_status()
        operation_url = resp.headers.get("Operation-Location")
        return await self._poll_result(operation_url)

    # ─── Polling ──────────────────────────────────────────────────────────

    async def _poll_result(self, operation_url: str, max_retries: int = 20) -> dict:
        """Espera a que Azure complete el análisis (polling con backoff)."""
        for attempt in range(max_retries):
            await asyncio.sleep(2 + attempt * 0.5)  # backoff progresivo
            resp = await self._client.get(
                operation_url, headers={"Ocp-Apim-Subscription-Key": self.api_key}
            )
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status")
            if status == "succeeded":
                return data.get("analyzeResult", {})
            if status == "failed":
                raise RuntimeError(f"Azure Document Intelligence falló: {data}")
        raise TimeoutError("Azure Document Intelligence no respondió a tiempo")

    # ─── Parsers de resultados ─────────────────────────────────────────────

    @staticmethod
    def extract_invoice_fields(result: dict) -> dict:
        """
        Extrae los campos más relevantes del resultado de prebuilt-invoice.
        Devuelve un dict con campos en español estandarizado.
        """
        docs = result.get("documents", [])
        if not docs:
            return {}

        fields = docs[0].get("fields", {})

        def get_value(field_name: str, value_type: str = "content") -> str | None:
            field = fields.get(field_name, {})
            if not field:
                return None
            return field.get(f"value{value_type.capitalize()}") or field.get("content")

        line_items = []
        for item in fields.get("Items", {}).get("valueArray", []):
            item_fields = item.get("valueObject", {})
            line_items.append(
                {
                    "descripcion": item_fields.get("Description", {}).get("content"),
                    "cantidad": item_fields.get("Quantity", {}).get("valueNumber"),
                    "precio_unit": item_fields.get("UnitPrice", {})
                    .get("valueCurrency", {})
                    .get("amount"),
                    "importe": item_fields.get("Amount", {}).get("valueCurrency", {}).get("amount"),
                }
            )

        return {
            "proveedor": get_value("VendorName"),
            "nif_proveedor": get_value("VendorTaxId"),
            "direccion_proveedor": get_value("VendorAddress"),
            "cliente": get_value("CustomerName"),
            "nif_cliente": get_value("CustomerTaxId"),
            "numero_factura": get_value("InvoiceId"),
            "fecha_factura": get_value("InvoiceDate"),
            "fecha_vencimiento": get_value("DueDate"),
            "base_imponible": fields.get("SubTotal", {}).get("valueCurrency", {}).get("amount"),
            "total_iva": fields.get("TotalTax", {}).get("valueCurrency", {}).get("amount"),
            "total_factura": fields.get("InvoiceTotal", {}).get("valueCurrency", {}).get("amount"),
            "moneda": fields.get("InvoiceTotal", {})
            .get("valueCurrency", {})
            .get("currencyCode", "EUR"),
            "lineas": line_items,
            "confidence": docs[0].get("confidence", 0),
        }
