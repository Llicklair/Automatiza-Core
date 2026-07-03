"""Candado de plan (solo < pro < gestoría) — enforcement AUTORITATIVO en backend.

Antes el plan solo filtraba la barra lateral del frontend: un cliente 'solo'
accedía a features 'pro' tecleando la URL o llamando a la API. require_plan lo
impide en el servidor, usando el plan del grant firmado (app.state.license_plan).
"""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.plan_gate import require_plan


def _app_with_gate(minimum: str) -> FastAPI:
    app = FastAPI()

    @app.get("/gated", dependencies=[Depends(require_plan(minimum))])
    async def gated():
        return {"ok": True}

    return app


def _client_with_plan(minimum: str, plan: str) -> TestClient:
    app = _app_with_gate(minimum)
    app.state.license_plan = plan
    return TestClient(app, raise_server_exceptions=False)


class TestRequirePlan:
    def test_solo_bloqueado_en_ruta_pro(self):
        r = _client_with_plan("pro", "solo").get("/gated")
        assert r.status_code == 402
        assert r.json()["detail"]["type"] == "plan_upgrade_required"
        assert r.json()["detail"]["required_plan"] == "pro"

    def test_pro_accede_a_ruta_pro(self):
        assert _client_with_plan("pro", "pro").get("/gated").status_code == 200

    def test_gestoria_accede_a_ruta_pro(self):
        # Jerarquía: gestoría cubre pro.
        assert _client_with_plan("pro", "gestoria").get("/gated").status_code == 200

    def test_pro_bloqueado_en_ruta_gestoria(self):
        assert _client_with_plan("gestoria", "pro").get("/gated").status_code == 402

    def test_gestoria_accede_a_ruta_gestoria(self):
        assert _client_with_plan("gestoria", "gestoria").get("/gated").status_code == 200

    def test_plan_desconocido_o_vacio_trata_como_solo(self):
        # Etiqueta inesperada / vacía nunca concede pro (fail-safe conservador).
        assert _client_with_plan("pro", "").get("/gated").status_code == 402
        assert _client_with_plan("pro", "starter").get("/gated").status_code == 402

    def test_solo_no_gatea_nada(self):
        # Una ruta que exige 'solo' es accesible con cualquier plan válido.
        assert _client_with_plan("solo", "solo").get("/gated").status_code == 200
