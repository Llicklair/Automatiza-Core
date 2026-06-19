"""E2E Contabilidad — flujo asiento → libro diario → cuentas anuales (Balance + P&G).

Verifica la integridad de la partida doble extremo a extremo, contra la API real:
  - cada asiento creado cuadra (Σdebe == Σhaber por asiento),
  - el libro diario completo cuadra (Σdebe == Σhaber global),
  - el sistema RECHAZA un asiento descuadrado (HTTP 400) — no se puede colar un descuadre,
  - los informes de cuentas anuales (Balance + P&G) y libro diario se generan (PDF 200).

Nota: P&G y Balance no exponen JSON (solo PDF, vía `generate_balance_pyg_pdf`), así que la
coherencia activo == pasivo + PN no es asertable por shape de respuesta. Aquí se asegura la
identidad fundamental de la partida doble (Σdebe == Σhaber), que es la raíz de "no descuadrar",
y que la generación de los estados financieros no rompe.
"""
from datetime import datetime

import pytest
from httpx import AsyncClient

# Mini-ejercicio coherente. account_code es un string libre (no hay PGC sembrado),
# se usan códigos del Plan General Contable por realismo.
_APERTURA = {
    "date": datetime(2026, 1, 1).isoformat(),
    "description": "Asiento de apertura",
    "lines": [
        {"account_code": "570", "account_name": "Caja", "debit": 10000.0, "credit": 0.0},
        {"account_code": "100", "account_name": "Capital social", "debit": 0.0, "credit": 10000.0},
    ],
}
_VENTA = {
    "date": datetime(2026, 3, 15).isoformat(),
    "description": "Venta de mercaderías con IVA 21%",
    "lines": [
        {"account_code": "430", "account_name": "Clientes", "debit": 1210.0, "credit": 0.0},
        {"account_code": "700", "account_name": "Ventas de mercaderías", "debit": 0.0, "credit": 1000.0},
        {"account_code": "477", "account_name": "IVA repercutido", "debit": 0.0, "credit": 210.0},
    ],
}
_COMPRA = {
    "date": datetime(2026, 4, 20).isoformat(),
    "description": "Compra de mercaderías con IVA 21%",
    "lines": [
        {"account_code": "600", "account_name": "Compras de mercaderías", "debit": 500.0, "credit": 0.0},
        {"account_code": "472", "account_name": "IVA soportado", "debit": 105.0, "credit": 0.0},
        {"account_code": "400", "account_name": "Proveedores", "debit": 0.0, "credit": 605.0},
    ],
}
_ASIENTOS = [_APERTURA, _VENTA, _COMPRA]

# Σdebe esperada del ejercicio: 10000 + 1210 + (500 + 105) = 11815 (= Σhaber).
_TOTAL_ESPERADO = 11815.0


def _balance(lines: list[dict]) -> tuple[float, float]:
    debit = round(sum(float(line["debit"]) for line in lines), 2)
    credit = round(sum(float(line["credit"]) for line in lines), 2)
    return debit, credit


class TestContabilidadE2E:
    @pytest.mark.asyncio
    async def test_flujo_asiento_a_cuentas_anuales(self, auth_client: AsyncClient):
        # 1) Crear los asientos del ejercicio; cada uno debe cuadrar.
        for asiento in _ASIENTOS:
            resp = await auth_client.post("/api/v1/accounting/journal", json=asiento)
            assert resp.status_code == 201, resp.text
            debit, credit = _balance(resp.json()["lines"])
            assert debit == credit, f"'{asiento['description']}' descuadra: debe={debit} haber={credit}"

        # 2) Libro diario: aparecen los 3 asientos y el conjunto cuadra (Σdebe == Σhaber global).
        diario = await auth_client.get("/api/v1/accounting/journal")
        assert diario.status_code == 200, diario.text
        entries = diario.json()
        assert len(entries) == len(_ASIENTOS)
        all_lines = [line for entry in entries for line in entry["lines"]]
        total_debit, total_credit = _balance(all_lines)
        assert total_debit == total_credit, f"libro diario descuadra: debe={total_debit} haber={total_credit}"
        assert total_debit == _TOTAL_ESPERADO

        # 3) Cuentas anuales (Balance + P&G) y libro diario en PDF se generan sin romper.
        params = {"start": "2026-01-01", "end": "2026-12-31"}
        for path in ("/api/v1/accounting/cuentas-anuales.pdf", "/api/v1/accounting/libro-diario.pdf"):
            pdf = await auth_client.get(path, params=params)
            assert pdf.status_code == 200, f"{path} -> {pdf.status_code}: {pdf.text[:300]}"
            assert pdf.headers["content-type"].startswith("application/pdf")
            assert pdf.content[:4] == b"%PDF", f"{path} no devolvió un PDF válido"

    @pytest.mark.asyncio
    async def test_asiento_descuadrado_se_rechaza(self, auth_client: AsyncClient):
        """No se puede colar un descuadre: Σdebe != Σhaber → 400 (raíz de la confianza fiscal)."""
        descuadrado = {
            "date": datetime(2026, 1, 5).isoformat(),
            "description": "Asiento descuadrado (debe != haber)",
            "lines": [
                {"account_code": "570", "account_name": "Caja", "debit": 100.0, "credit": 0.0},
                {"account_code": "100", "account_name": "Capital", "debit": 0.0, "credit": 50.0},
            ],
        }
        resp = await auth_client.post("/api/v1/accounting/journal", json=descuadrado)
        assert resp.status_code == 400, resp.text
        # Y no debe haber quedado registrado en el libro diario.
        diario = await auth_client.get("/api/v1/accounting/journal")
        assert diario.status_code == 200
        assert diario.json() == []
