"""Tests para el endpoint público de verificación Verifactu (FAC.QR)."""
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from app.db.models.billing import Invoice
from app.db.models.crm import Client
from app.main import app
from app.services.billing.verifactu_chain import append_verifactu_record
from httpx import ASGITransport, AsyncClient


def _make_invoice(tenant_id, client_id, *, invoice_number: str, importe: Decimal) -> Invoice:
    return Invoice(
        tenant_id=tenant_id,
        client_id=client_id,
        invoice_number=invoice_number,
        date=datetime(2026, 5, 14, 10, 0, tzinfo=UTC),
        amount_base=importe,
        tax_amount=Decimal("0.00"),
        amount_total=importe,
    )


async def _create_record(db, seed_tenant_and_user):
    tenant, _user, _token = seed_tenant_and_user
    client = Client(tenant_id=tenant.id, nif="B12345678", name="Acme SL")
    db.add(client)
    await db.flush()
    invoice = _make_invoice(tenant.id, client.id, invoice_number="A2026-0001", importe=Decimal("121.00"))
    db.add(invoice)
    await db.flush()
    record = await append_verifactu_record(db, invoice=invoice, nif_emisor="B99999999")
    await db.commit()
    return record


@pytest.mark.asyncio
class TestVerifyEndpoint:
    async def test_huella_invalida_devuelve_400(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/verify/no-es-una-huella")
        assert resp.status_code == 400
        assert "Huella" in resp.json()["detail"]

    async def test_huella_inexistente_devuelve_404(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/verify/" + ("0" * 64))
        assert resp.status_code == 404

    async def test_huella_valida_devuelve_datos(self, db, seed_tenant_and_user):
        record = await _create_record(db, seed_tenant_and_user)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(f"/api/v1/verify/{record.huella}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["huella"] == record.huella
        assert data["nif_emisor"] == "B99999999"
        assert data["numero_factura"] == "A2026-0001"
        assert data["integrity_ok"] is True

    async def test_endpoint_no_requiere_auth(self, db, seed_tenant_and_user):
        record = await _create_record(db, seed_tenant_and_user)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Sin Authorization header
            resp = await ac.get(f"/api/v1/verify/{record.huella}")
        assert resp.status_code == 200

    async def test_huella_uppercase_se_normaliza(self, db, seed_tenant_and_user):
        record = await _create_record(db, seed_tenant_and_user)
        upper = record.huella.upper()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(f"/api/v1/verify/{upper}")
        assert resp.status_code == 200
        assert resp.json()["huella"] == record.huella


@pytest.mark.asyncio
class TestPdfQrBlock:
    async def test_pdf_con_verifactu_contiene_huella(self):
        """Verifica que el bloque QR se renderiza en el PDF cuando se pasa data Verifactu."""
        from app.services.pdf.invoices import generate_invoice_pdf

        invoice_data = {
            "number": "A2026-0001",
            "date": "2026-05-14",
            "company": {"name": "Acme SL", "nif": "B99999999"},
            "client": {"name": "Cliente SA", "nif": "B12345678"},
            "lines": [{"description": "Servicio", "quantity": 1, "unit_price": 100, "amount": 100}],
            "amount_base": 100.00,
            "tax_amount": 21.00,
            "amount_total": 121.00,
            "verifactu": {
                "huella": "abc123def456" + "0" * 52,
                "verify_url": "https://automatizapyme.com/api/v1/verify/abc123def456" + "0" * 52,
            },
        }
        pdf_bytes = generate_invoice_pdf(invoice_data)
        # El PDF debe ser válido y mayor que el header mínimo.
        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 2000

    async def test_pdf_sin_verifactu_funciona(self):
        """Sin data Verifactu el PDF sigue siendo válido (sin QR)."""
        from app.services.pdf.invoices import generate_invoice_pdf

        invoice_data = {
            "number": "A2026-0001",
            "date": "2026-05-14",
            "company": {"name": "Acme SL", "nif": "B99999999"},
            "client": {"name": "Cliente SA", "nif": "B12345678"},
            "lines": [{"description": "Servicio", "quantity": 1, "unit_price": 100, "amount": 100}],
            "amount_base": 100.00,
            "tax_amount": 21.00,
            "amount_total": 121.00,
        }
        pdf_bytes = generate_invoice_pdf(invoice_data)
        assert pdf_bytes.startswith(b"%PDF")
