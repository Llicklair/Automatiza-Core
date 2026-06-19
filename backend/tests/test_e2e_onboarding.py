"""E2E Onboarding — wizard de alta → simulación del Modelo 303 → verificación REGAP (mock).

Cruza varios endpoints contra la API real (SQLite en memoria, sin LLM):
  - el wizard arranca sin completar y queda completado al marcar sus 5 pasos,
  - la simulación del Modelo 303 devuelve un resultado coherente (devengado − deducible),
  - el alta REGAP recorre su máquina de estados (start → grant → verify) hasta `verified`.

REGAP está mockeado (DEC.14 pendiente): el apoderamiento simulado es VIGENTE, así que `verify`
siempre pasa a `verified`. El seed crea un usuario admin, requerido por los POST de REGAP.
"""
import pytest
from httpx import AsyncClient


class TestOnboardingE2E:
    @pytest.mark.asyncio
    async def test_wizard_simulacion303_regap(self, auth_client: AsyncClient):
        # 1) Wizard: arranca sin completar; al marcar los 5 pasos queda completado.
        estado = await auth_client.get("/api/v1/onboarding/wizard")
        assert estado.status_code == 200, estado.text
        assert estado.json()["completed_at"] is None

        ultimo = None
        for step in ("company", "cert", "data", "use_case", "llm_config"):
            ultimo = await auth_client.patch(
                "/api/v1/onboarding/wizard", json={"step": step, "value": True}
            )
            assert ultimo.status_code == 200, ultimo.text
        assert ultimo.json()["completed_at"] is not None

        # 2) Simulación del Modelo 303 (datos de ejemplo, sin facturas).
        sim = await auth_client.get(
            "/api/v1/onboarding/wizard/simulate/303", params={"quarter": 1, "year": 2026}
        )
        assert sim.status_code == 200, sim.text
        s = sim.json()
        assert s["is_simulation"] is True
        totals = s["totals"]
        assert totals["resultado"] > 0
        assert totals["resultado"] == pytest.approx(
            round(totals["devengado_quota"] - totals["deducible_quota"], 2)
        )

        # 3) REGAP (mock): identificación → apoderamiento → verificación.
        start = await auth_client.post(
            "/api/v1/onboarding/regap/start", json={"auth_method": "clave_pin"}
        )
        assert start.status_code == 200, start.text
        grant = await auth_client.post("/api/v1/onboarding/regap/grant")
        assert grant.status_code == 200, grant.text
        verify = await auth_client.post(
            "/api/v1/onboarding/regap/verify", json={"nif_cliente": "B12345678"}
        )
        assert verify.status_code == 200, verify.text
        v = verify.json()
        assert v["status"] == "verified"
        assert v["verified_at"] is not None
