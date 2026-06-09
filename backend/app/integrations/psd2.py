"""
Integración bancaria PSD2 usando Nordigen (GoCardless).
API gratuita que cubre +2.500 bancos europeos, incluyendo todos los españoles.
Docs: https://nordigen.com/en/account_information_documenation/api-documention/

Bancos españoles soportados: Santander, BBVA, CaixaBank, Sabadell, Bankinter,
ING, Openbank, UniCaja, Ibercaja, Kutxabank, etc.
"""

from datetime import date

import httpx

NORDIGEN_BASE = "https://bankaccountdata.gocardless.com/api/v2"


class NordigenClient:
    """
    Cliente async para GoCardless Bank Account Data (ex-Nordigen).
    Flujo OAuth PSD2:
      1. POST /token/new/       → access/refresh token
      2. GET  /institutions/    → listar bancos disponibles en ES
      3. POST /requisitions/    → crear link de autorización
      4. GET  /requisitions/{id} → obtener IDs de cuentas
      5. GET  /accounts/{id}/   → obtener saldos y transacciones
    """

    def __init__(self, secret_id: str, secret_key: str):
        self._secret_id = secret_id
        self._secret_key = secret_key
        self._access_token: str | None = None
        self._client = httpx.AsyncClient(base_url=NORDIGEN_BASE, timeout=30.0)

    async def close(self):
        await self._client.aclose()

    # ─── Autenticación ────────────────────────────────────────────────────

    async def _get_access_token(self) -> str:
        """Obtiene o renueva el token de acceso."""
        if self._secret_id == "DEMO_PSD2_ID":
            return "demo_token_123"

        if self._access_token:
            return self._access_token
        resp = await self._client.post(
            "/token/new/",
            json={"secret_id": self._secret_id, "secret_key": self._secret_key},
        )
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access"]
        return self._access_token

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._access_token}"}

    # ─── Bancos ───────────────────────────────────────────────────────────

    async def list_institutions(self, country: str = "ES") -> list[dict]:
        """Lista todos los bancos disponibles en un país."""
        await self._get_access_token()
        resp = await self._client.get(
            "/institutions/",
            params={"country": country},
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    # ─── Proceso de vinculación ───────────────────────────────────────────

    async def create_requisition(
        self,
        institution_id: str,
        redirect_url: str,
        reference: str,
        language: str = "ES",
    ) -> dict:
        """
        Crea una requisition (proceso de vinculación).
        Devuelve un `link` que debes redirigir al usuario para que autorice.
        """
        await self._get_access_token()
        resp = await self._client.post(
            "/requisitions/",
            json={
                "redirect": redirect_url,
                "institution_id": institution_id,
                "reference": reference,
                "agreement": "",
                "user_language": language,
            },
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()
        # Respuesta incluye: { "id": "...", "link": "https://ob.gocardless.com/..." }

    async def get_requisition(self, requisition_id: str) -> dict:
        """
        Consulta el estado de una requisition.
        Una vez autorizada, `accounts` contendrá los IDs de las cuentas.
        """
        await self._get_access_token()
        resp = await self._client.get(
            f"/requisitions/{requisition_id}/",
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    # ─── Cuentas ──────────────────────────────────────────────────────────

    async def get_account_details(self, account_id: str) -> dict:
        """Metadatos de una cuenta (IBAN, nombre, moneda)."""
        if self._secret_id == "DEMO_PSD2_ID":
            return {"iban": "ES9121000418401234567891", "name": "Cuenta Principal Empresa"}

        await self._get_access_token()
        resp = await self._client.get(
            f"/accounts/{account_id}/details/",
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        return resp.json().get("account", {})

    async def get_account_balances(self, account_id: str) -> list[dict]:
        """Saldos actuales de una cuenta (disponible, reservado)."""
        if self._secret_id == "DEMO_PSD2_ID":
            return [
                {
                    "balanceType": "interimAvailable",
                    "balanceAmount": {"amount": "14250.00", "currency": "EUR"},
                }
            ]

        await self._get_access_token()
        resp = await self._client.get(
            f"/accounts/{account_id}/balances/",
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        return resp.json().get("balances", [])

    async def get_transactions(
        self,
        account_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        """
        Obtiene las transacciones de una cuenta.
        Devuelve dict con "booked" y "pending".
        """
        if self._secret_id == "DEMO_PSD2_ID":
            return {
                "booked": [
                    {
                        "transactionId": "tx_1",
                        "valueDate": "2023-10-01",
                        "transactionAmount": {"amount": "-1500.00", "currency": "EUR"},
                        "remittanceInformationUnstructured": "Pago Alquiler Oficina Octubre",
                        "creditorName": "Inmobiliaria Centro SL",
                    },
                    {
                        "transactionId": "tx_2",
                        "valueDate": "2023-10-05",
                        "transactionAmount": {"amount": "3400.00", "currency": "EUR"},
                        "remittanceInformationUnstructured": "Cobro Factura 2023-44",
                        "debtorName": "Cliente Importante SA",
                    },
                    {
                        "transactionId": "tx_3",
                        "valueDate": "2023-10-08",
                        "transactionAmount": {"amount": "-250.00", "currency": "EUR"},
                        "remittanceInformationUnstructured": "Recibo Luz",
                        "creditorName": "Iberdrola Clientes",
                    },
                ]
            }

        await self._get_access_token()
        params = {}
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()

        resp = await self._client.get(
            f"/accounts/{account_id}/transactions/",
            params=params,
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        return resp.json().get("transactions", {})

    # ─── Utilidades ───────────────────────────────────────────────────────

    @staticmethod
    def normalize_transactions(raw_transactions: dict) -> list[dict]:
        """
        Normaliza las transacciones al formato interno de AutomatizaCore.
        PSD2 no tiene un formato único — diferencia por banco.
        """
        normalized = []
        for tx in raw_transactions.get("booked", []):
            amount_info = tx.get("transactionAmount", {})
            normalized.append(
                {
                    "id": tx.get("transactionId") or tx.get("internalTransactionId", ""),
                    "fecha": tx.get("valueDate") or tx.get("bookingDate", ""),
                    "importe": float(amount_info.get("amount", 0)),
                    "moneda": amount_info.get("currency", "EUR"),
                    "concepto": tx.get("remittanceInformationUnstructured")
                    or tx.get("remittanceInformationStructured", ""),
                    "deudor": tx.get("debtorName", ""),
                    "acreedor": tx.get("creditorName", ""),
                    "iban_deudor": tx.get("debtorAccount", {}).get("iban", ""),
                    "iban_acreedor": tx.get("creditorAccount", {}).get("iban", ""),
                    "estado": "confirmada",
                    "tipo": "cargo" if float(amount_info.get("amount", 0)) < 0 else "abono",
                }
            )
        return normalized
