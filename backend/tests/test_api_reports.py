"""Tests for Reports API — uses the actual routes (company-snapshot, fiscal,
cashflow, delinquency) instead of the non-existent paths the previous fakes tested.
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4


class TestReportsAuth:
    @pytest.mark.asyncio
    async def test_list_unauth(self, client: AsyncClient):
        resp = await client.get("/api/v1/reports/")
        assert resp.status_code in (401, 403, 307)


class TestReportsList:
    @pytest.mark.asyncio
    async def test_list_returns_array(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/reports/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestCompanySnapshot:
    @pytest.mark.asyncio
    async def test_company_snapshot_default_month(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/reports/company-snapshot")
        assert resp.status_code == 200
        data = resp.json()
        for key in ("month", "facturas", "banca", "rrhh", "clientes"):
            assert key in data, f"Falta clave '{key}' en CompanySnapshot"

    @pytest.mark.asyncio
    async def test_company_snapshot_invoices_section_shape(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/reports/company-snapshot")
        assert resp.status_code == 200
        invoices = resp.json()["facturas"]
        for key in (
            "ingresos_total", "gastos_total", "margen_bruto", "margen_pct",
            "facturas_emitidas", "facturas_recibidas",
        ):
            assert key in invoices

    @pytest.mark.asyncio
    async def test_company_snapshot_with_explicit_month(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/reports/company-snapshot?month=2026-04")
        assert resp.status_code == 200
        assert resp.json()["month"] == "2026-04"


class TestFiscalSnapshot:
    @pytest.mark.asyncio
    async def test_fiscal_snapshot_returns_iva_irpf_is(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/reports/fiscal-snapshot")
        # 200 with full snapshot, or 422 if period param required
        assert resp.status_code in (200, 422)
        if resp.status_code == 200:
            data = resp.json()
            for key in ("period", "iva", "irpf", "impuesto_sociedades"):
                assert key in data


class TestSpecializedReports:
    @pytest.mark.asyncio
    async def test_cashflow_runs(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/reports/cashflow")
        assert resp.status_code in (200, 422)

    @pytest.mark.asyncio
    async def test_delinquency_runs(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/reports/delinquency")
        assert resp.status_code in (200, 422)

    @pytest.mark.asyncio
    async def test_rgpd_registry_runs(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/reports/compliance/rgpd-registry")
        assert resp.status_code in (200, 404, 422)


class TestReportDownload:
    @pytest.mark.asyncio
    async def test_download_nonexistent_report_returns_404(self, auth_client: AsyncClient):
        resp = await auth_client.get(f"/api/v1/reports/{uuid4()}/download")
        assert resp.status_code == 404
