"""E2E Inventario — producto → entrada por lote (con caducidad) → salida bajo mínimo → reposición.

Cruza varios endpoints contra la API real (SQLite en memoria, sin LLM):
  - se crea un producto con punto de pedido (stock_min_alert),
  - entra un lote con fecha de caducidad (FEFO) que sube el stock por encima del mínimo,
  - estando por encima del mínimo NO aparece en reposición,
  - una salida deja el stock por debajo del mínimo → el producto SÍ aparece en reposición.
"""
import pytest
from httpx import AsyncClient


class TestInventarioE2E:
    @pytest.mark.asyncio
    async def test_producto_lote_salida_reorder(self, auth_client: AsyncClient):
        # 1) Producto con punto de pedido (mínimo 10), sin stock inicial.
        prod = await auth_client.post("/api/v1/products", json={
            "name": "Leche entera 1L", "sku": "LCH-1", "unit": "ud",
            "price": 1.20, "cost_price": 0.50,
            "stock_quantity": 0, "stock_min_alert": 10,
        })
        assert prod.status_code == 201, prod.text
        pid = prod.json()["id"]

        # 2) Entrada por lote con caducidad (FEFO) → stock sube a 30.
        lot = await auth_client.post(f"/api/v1/products/{pid}/lots", json={
            "lot_number": "L-001", "quantity": 30,
            "expiry_date": "2026-12-31", "cost_price": 0.50,
        })
        assert lot.status_code == 201, lot.text

        # Con 30 > mínimo 10, el producto NO debe figurar en reposición.
        sug0 = await auth_client.get("/api/v1/inventory/reorder-suggestions")
        assert sug0.status_code == 200
        assert pid not in [it["product_id"] for it in sug0.json()]

        # 3) Salida que deja el stock bajo mínimo (30 − 25 = 5).
        out = await auth_client.post(f"/api/v1/products/{pid}/stock-movements", json={
            "movement_type": "salida", "quantity": 25,
        })
        assert out.status_code == 201, out.text
        assert out.json()["stock_after"] == 5

        # 4) Ahora aparece en reposición, por debajo de su punto de pedido.
        sug = await auth_client.get("/api/v1/inventory/reorder-suggestions")
        assert sug.status_code == 200
        item = next(it for it in sug.json() if it["product_id"] == pid)
        assert item["current_stock"] == 5
        assert item["reorder_point"] == 10
        assert item["suggested_qty"] >= 1

        # Y también en el listado filtrado por stock bajo.
        low = await auth_client.get("/api/v1/products", params={"status": "low_stock"})
        assert low.status_code == 200
        assert pid in [p["id"] for p in low.json()]
