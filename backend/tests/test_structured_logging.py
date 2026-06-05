"""Tests para `structured_logging` y `diagnostic_bundle` (CONT.LOG)."""
import io
import json
import logging
import zipfile

import pytest
from app.core.structured_logging import JSONFormatter, get_log_dir
from app.main import app
from app.services.system.diagnostic_bundle import build_diagnostic_bundle
from httpx import ASGITransport, AsyncClient


class TestJSONFormatter:
    def test_emite_json_line_valida(self):
        formatter = JSONFormatter(app_version="1.2.3")
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="x.py", lineno=42,
            msg="hello world", args=(), exc_info=None, func="test_func",
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert data["message"] == "hello world"
        assert data["app_version"] == "1.2.3"
        assert data["function"] == "test_func"
        assert data["line"] == 42
        assert "timestamp" in data

    def test_scrub_aplicado_a_mensaje(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="x.py", lineno=1,
            msg="cliente 12345678A con IBAN ES9121000418450200051332",
            args=(), exc_info=None,
        )
        data = json.loads(formatter.format(record))
        assert "12345678A" not in data["message"]
        assert "ES9121" not in data["message"]
        assert "[REDACTED-NIF]" in data["message"]
        assert "[REDACTED-IBAN]" in data["message"]

    def test_extra_se_serializa(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="t", level=logging.INFO, pathname="x.py", lineno=1,
            msg="ok", args=(), exc_info=None,
        )
        record.invoice_id = "abc-123"
        record.amount = 100
        output = json.loads(formatter.format(record))
        assert output["extra"]["invoice_id"] == "abc-123"
        assert output["extra"]["amount"] == 100


class TestGetLogDir:
    def test_devuelve_path_existente(self):
        log_dir = get_log_dir()
        assert log_dir.exists()
        assert log_dir.is_dir()


@pytest.mark.asyncio
class TestDiagnosticBundle:
    async def test_bundle_contiene_info_basica(self, db):
        zip_bytes = await build_diagnostic_bundle(db)
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            names = set(zf.namelist())
            assert "info.json" in names
            assert "precondiciones.json" in names
            assert "alembic_version.txt" in names

            info = json.loads(zf.read("info.json").decode("utf-8"))
            assert "generated_at" in info
            assert "app_version" in info
            assert "python_version" in info
            assert "os_family" in info

    async def test_bundle_zip_valido(self, db):
        zip_bytes = await build_diagnostic_bundle(db)
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            # No debe haber CRC errors
            bad = zf.testzip()
            assert bad is None

    async def test_endpoint_requiere_auth(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/system/diagnostic-bundle")
        # Sin header Authorization, HTTPBearer(auto_error=True) responde 403.
        assert resp.status_code == 403

    async def test_endpoint_devuelve_zip(self, db, seed_tenant_and_user):
        _, _, token = seed_tenant_and_user
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(
                "/api/v1/system/diagnostic-bundle",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        assert "attachment" in resp.headers.get("content-disposition", "")
        # Verificar que el contenido es un ZIP válido
        with zipfile.ZipFile(io.BytesIO(resp.content), "r") as zf:
            assert zf.testzip() is None
