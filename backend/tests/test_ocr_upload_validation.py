"""Hardening: los endpoints OCR rechazan ficheros con extensión no soportada
ANTES de invocar el OCR/LLM (deterministas, no requieren API key).

Cubre los 3 endpoints (sibling-complete):
  - POST /api/v1/hr/expenses/scan   (scan_expense_receipt)
  - POST /api/v1/invoices/scan      (scan_invoice)
  - POST /api/v1/invoices/scan-batch (scan_invoices_batch)
"""

import pytest

# Códigos que cuentan como "rechazo por validación" (no un 500 genérico).
_VALIDATION_REJECT = {400, 415}


@pytest.mark.asyncio
async def test_scan_expense_rejects_exe(auth_client):
    """Un .exe en /hr/expenses/scan se rechaza con 415 sin llamar al LLM."""
    files = {"file": ("malware.exe", b"MZ\x90\x00 not an image", "application/octet-stream")}
    resp = await auth_client.post("/api/v1/hr/expenses/scan", files=files)
    assert resp.status_code in _VALIDATION_REJECT, resp.text
    # Es un rechazo de validación, NO un 500 genérico del scanner.
    assert resp.status_code != 500
    assert "no soportado" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_scan_invoice_rejects_txt(auth_client):
    """Un .txt en /invoices/scan se rechaza con 415 sin llamar al LLM."""
    files = {"file": ("notas.txt", b"hola, esto no es una factura", "text/plain")}
    resp = await auth_client.post("/api/v1/invoices/scan", files=files)
    assert resp.status_code in _VALIDATION_REJECT, resp.text
    assert resp.status_code != 500
    assert "no soportado" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_scan_invoice_rejects_zip(auth_client):
    """.zip está en el allowlist de documents pero NO en el de OCR → 415."""
    files = {"file": ("docs.zip", b"PK\x03\x04 fake zip", "application/zip")}
    resp = await auth_client.post("/api/v1/invoices/scan", files=files)
    assert resp.status_code in _VALIDATION_REJECT, resp.text


@pytest.mark.asyncio
async def test_scan_batch_records_invalid_per_file(auth_client):
    """El lote NO se tumba: el .exe se devuelve con su error por-fichero (200)."""
    files = [
        ("files", ("malware.exe", b"MZ bad", "application/octet-stream")),
        ("files", ("tambien.txt", b"texto plano", "text/plain")),
    ]
    resp = await auth_client.post("/api/v1/invoices/scan-batch", files=files)
    assert resp.status_code == 200, resp.text
    results = resp.json()["results"]
    assert len(results) == 2
    for r in results:
        assert r["extracted"] is None
        assert r["error"] is not None
        assert "no soportado" in r["error"].lower()


# ── Control unitario: los formatos OCR legítimos NO se rechazan ───────────────


def test_validate_helper_accepts_legit_formats():
    """La función de validación acepta jpg/jpeg/png/webp/gif (+pdf en facturas)
    sin lanzar — garantiza que no hay sobre-rechazo de formatos válidos."""
    from app.services.ocr._upload_validation import (
        INVOICE_EXTENSIONS,
        RECEIPT_EXTENSIONS,
        validate_ocr_upload,
    )

    class _FakeUpload:
        def __init__(self, filename):
            self.filename = filename

    for name in ("ticket.jpg", "ticket.JPEG", "foto.png", "img.webp", "scan.gif"):
        validate_ocr_upload(_FakeUpload(name), RECEIPT_EXTENSIONS)  # no debe lanzar

    for name in ("factura.pdf", "factura.PNG", "factura.jpeg"):
        validate_ocr_upload(_FakeUpload(name), INVOICE_EXTENSIONS)  # no debe lanzar

    # Receipts NO soporta PDF → debe rechazarlo.
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        validate_ocr_upload(_FakeUpload("factura.pdf"), RECEIPT_EXTENSIONS)
    assert exc.value.status_code == 415
