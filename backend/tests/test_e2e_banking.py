"""E2E Banca — flujo importar N43 → listar/resumen → conciliar movimiento ↔ factura.

Cruza varios endpoints contra la API real (SQLite en memoria, sin LLM):
  - importa un extracto Norma 43 (Cuaderno 43 AEB) → se crean los movimientos,
  - el movimiento de abono concilia contra una factura emitida del mismo importe,
  - al conciliar, el movimiento queda `reconciled` y la factura pasa a `paid`.

El fichero N43 se construye inline (mismo formato que `test_norma43_parser.py`) para no
depender de un fixture externo; el registro 33 cuadra nº de apuntes y totales (si no, el
parser lanza `Norma43Error` → 422).

Orden importante: se importa ANTES de crear la factura, porque el import ejecuta
`auto_reconcile` al final; así el match se prueba por la vía manual (sugerencias → reconcile).
"""
import io
from datetime import datetime

import pytest
from httpx import AsyncClient

# ── Generador de N43 mínimo válido (copiado de test_norma43_parser.py) ──────────


def _line(code: str, body: str) -> str:
    return (code + body).ljust(80)


def _mov22(fecha: str, dh: str, cents: int, doc: str = "0000000000") -> str:
    # 22 + entidad(4)+oficina(4) + f.op(6)+f.valor(6) + común(2)+propio(3) + D/H(1) + importe(14) + doc(10)
    return _line("22", "00810001" + fecha + fecha + "02" + "000" + dh + f"{cents:014d}" + doc)


def _build_n43(movs: list[tuple[str, str, int]], saldo_inicial_cents: int = 100000) -> str:
    lines = [
        _line(
            "11",
            "00810001" + "0123456789" + "260601" + "260630" + "2"
            + f"{saldo_inicial_cents:014d}" + "978" + "1" + "EMPRESA DEMO SL",
        )
    ]
    for fecha, dh, cents in movs:
        lines.append(_mov22(fecha, dh, cents))
        lines.append(_line("23", "01TRANSFERENCIA DE PRUEBA"))
    cargos = [c for _, dh, c in movs if dh == "1"]
    abonos = [c for _, dh, c in movs if dh == "2"]
    saldo_final = saldo_inicial_cents - sum(cargos) + sum(abonos)
    lines.append(
        _line(
            "33",
            "00810001" + "0123456789"
            + f"{len(cargos):05d}" + f"{sum(cargos):014d}"
            + f"{len(abonos):05d}" + f"{sum(abonos):014d}"
            + ("2" if saldo_final >= 0 else "1") + f"{abs(saldo_final):014d}" + "978",
        )
    )
    lines.append(_line("88", "9" * 18 + f"{len(lines) + 1:06d}"))
    return "\n".join(lines)


# Abono 1210,00€ (= factura con base 1000 + IVA 21%) y cargo 250,50€ (sin contrapartida).
_ABONO_EUR = 1210.0
_CARGO_EUR = 250.50


class TestBancaE2E:
    @pytest.mark.asyncio
    async def test_import_n43_y_conciliacion(self, auth_client: AsyncClient):
        # 1) Importar el extracto N43 (todavía sin facturas → no auto-concilia nada).
        content = _build_n43([("260605", "2", 121000), ("260610", "1", 25050)])
        files = {"file": ("extracto.n43", io.BytesIO(content.encode("latin-1")), "text/plain")}
        imp = await auth_client.post("/api/v1/import/bank-statement-n43", files=files)
        assert imp.status_code in (200, 201), imp.text

        # 2) Los dos movimientos quedan registrados, con importe y signo correctos.
        txs = (await auth_client.get("/api/v1/banking/transactions")).json()
        assert len(txs) == 2, txs
        abono = next(t for t in txs if t["amount"] > 0)
        cargo = next(t for t in txs if t["amount"] < 0)
        assert abono["amount"] == pytest.approx(_ABONO_EUR)
        assert cargo["amount"] == pytest.approx(-_CARGO_EUR)
        assert abono["status"] == "unreconciled"

        # 3) El resumen bancario responde.
        summary = await auth_client.get("/api/v1/banking/summary")
        assert summary.status_code == 200, summary.text

        # 4) Crear cliente + factura emitida del mismo importe que el abono (1210,00).
        client_id = (await auth_client.post("/api/v1/clients", json={
            "name": "Empresa Cliente S.A.", "nif": "A12345678", "email": "cliente@empresa.com",
        })).json()["id"]
        invoice = (await auth_client.post(f"/api/v1/clients/{client_id}/invoices", json={
            "date": datetime(2026, 6, 5).isoformat(),
            "status": "pending",
            "invoice_type": "issued",
            "lines": [{"description": "Servicios", "quantity": 1.0,
                       "unit_price": 1000.0, "tax_percentage": 21.0}],
        })).json()
        invoice_id = invoice["id"]

        # 5) Sugerencias de conciliación: el abono debe proponer esa factura.
        sug_resp = await auth_client.get("/api/v1/banking/reconciliation/suggestions")
        assert sug_resp.status_code == 200, sug_resp.text
        entry = next(e for e in sug_resp.json() if e["tx"]["id"] == abono["id"])
        suggested_ids = [s["id"] for s in entry["suggestions"]]
        assert invoice_id in suggested_ids, f"la factura {invoice_id} no se sugirió: {entry}"

        # 6) Conciliar el abono contra la factura.
        rec = await auth_client.post(
            f"/api/v1/banking/transactions/{abono['id']}/reconcile",
            json={"invoice_id": invoice_id},
        )
        assert rec.status_code == 200, rec.text

        # 7) El movimiento queda conciliado y la factura pasa a pagada.
        txs_after = (await auth_client.get("/api/v1/banking/transactions")).json()
        abono_after = next(t for t in txs_after if t["id"] == abono["id"])
        assert abono_after["status"] == "reconciled"
        assert abono_after["invoice_id"] == invoice_id
        inv_after = await auth_client.get(f"/api/v1/invoices/{invoice_id}")
        assert inv_after.status_code == 200
        assert inv_after.json()["status"] == "paid"
