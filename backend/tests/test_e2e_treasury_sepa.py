"""E2E Tesorería + SEPA — cashflow → remesa de adeudos (pain.008) y transferencias (pain.001).

Cruza varios endpoints contra la API real (SQLite en memoria, sin LLM):
  - la proyección de cashflow responde con su estructura,
  - se genera una remesa de adeudos SEPA (cobros a clientes, pain.008.001.02),
  - se genera una remesa de transferencias SEPA (pagos a proveedores, pain.001.001.03),
  - la remesa queda registrada, se descarga su XML y avanza de estado (generated → sent).

Notas: no existe validación XSD del SEPA en el repo (solo namespaces) → se aserta el XML por
namespace y por la suma de control. Las fechas de remesa deben ser >= hoy (se usa mañana).
El IBAN del acreedor/deudor va en el body (el Tenant no tiene columna IBAN).
"""
from datetime import date, timedelta
from xml.etree.ElementTree import fromstring

import pytest
from httpx import AsyncClient

# IBANs/creditor_id de prueba (los mismos que usan los tests de remesas existentes).
_CREDITOR_IBAN = "ES9121000418450200051332"
_DEBTOR_IBAN = "ES7921000813610123456789"
_CREDITOR_ID = "ES12000B12345678"
_NS008 = "urn:iso:std:iso:20022:tech:xsd:pain.008.001.02"
_NS001 = "urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"


class TestTesoreriaSepaE2E:
    @pytest.mark.asyncio
    async def test_cashflow_y_remesas_sepa(self, auth_client: AsyncClient):
        manana = (date.today() + timedelta(days=1)).isoformat()

        # 1) Cashflow: la proyección responde con su estructura.
        cf = await auth_client.get(
            "/api/v1/treasury/cashflow/projection", params={"days_ahead": 30}
        )
        assert cf.status_code == 200, cf.text
        body = cf.json()
        assert "series" in body and "summary" in body
        assert {"total_in", "total_out", "net"} <= set(body["summary"])

        # 2) Remesa de adeudos (cobros a clientes) — pain.008.
        pain008 = await auth_client.post("/api/v1/treasury/sepa/pain008", json={
            "collection_date": manana,
            "creditor_iban": _CREDITOR_IBAN,
            "creditor_id": _CREDITOR_ID,
            "orders": [{
                "debtor_name": "Cliente Uno S.L.",
                "debtor_iban": _DEBTOR_IBAN,
                "amount_eur": 150.0,
                "concept": "Cuota mensual",
                "mandate_id": "MNDT-001",
                "mandate_date": "2025-01-15",
                "sequence_type": "RCUR",
            }],
        })
        assert pain008.status_code == 200, pain008.text
        dd = pain008.json()
        assert _NS008 in fromstring(dd["xml"]).tag
        assert dd["summary"]["control_sum_eur"] == 150.0
        assert int(dd["summary"]["nb_of_txs"]) == 1
        remittance_id = dd["remittance_id"]

        # 3) Remesa de transferencias (pagos a proveedores) — pain.001.
        pain001 = await auth_client.post("/api/v1/treasury/sepa/pain001", json={
            "execution_date": manana,
            "debtor_iban": _CREDITOR_IBAN,
            "orders": [{
                "creditor_name": "Proveedor Dos S.A.",
                "creditor_iban": _DEBTOR_IBAN,
                "amount_eur": 80.50,
                "concept": "Factura proveedor",
            }],
        })
        assert pain001.status_code == 200, pain001.text
        assert _NS001 in fromstring(pain001.json()["xml"]).tag

        # 4) La remesa de adeudos queda registrada, se descarga su XML y avanza de estado.
        detalle = await auth_client.get(f"/api/v1/treasury/remittances/{remittance_id}")
        assert detalle.status_code == 200, detalle.text

        listado = await auth_client.get("/api/v1/treasury/remittances")
        assert listado.status_code == 200
        assert remittance_id in [r["id"] for r in listado.json()["items"]]

        xml_dl = await auth_client.get(f"/api/v1/treasury/remittances/{remittance_id}/xml")
        assert xml_dl.status_code == 200
        assert _NS008 in xml_dl.text

        avance = await auth_client.post(
            f"/api/v1/treasury/remittances/{remittance_id}/status",
            json={"status": "sent"},
        )
        assert avance.status_code == 200, avance.text
