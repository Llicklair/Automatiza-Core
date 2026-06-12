"""Tests de endurecimiento de licencia: middleware fail-closed + DEVMODE gateado."""
import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.core import license as lic_mod
from app.core.license import validate_license
from app.middleware.license_check import LicenseCheckMiddleware


def _mk_app() -> Starlette:
    async def ok(request):  # noqa: ARG001
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/api/v1/erp/x", ok), Route("/health", ok)])
    app.add_middleware(LicenseCheckMiddleware)
    return app


class TestMiddlewareFailClosed:
    def test_protected_blocked_when_flag_unset(self):
        # license_valid nunca fijado → fail-closed → 402
        client = TestClient(_mk_app())
        assert client.get("/api/v1/erp/x").status_code == 402

    def test_health_always_allowed(self):
        client = TestClient(_mk_app())
        assert client.get("/health").status_code == 200

    def test_protected_allowed_when_valid(self):
        app = _mk_app()
        app.state.license_valid = True
        assert TestClient(app).get("/api/v1/erp/x").status_code == 200


@pytest.mark.asyncio
class TestDevmodeGate:
    async def test_devmode_bypass_in_dev(self, monkeypatch):
        monkeypatch.setattr(lic_mod.settings, "AP_DEVMODE", "1")
        monkeypatch.delenv("AUTOMATIZA_RELEASE", raising=False)
        res = await validate_license()
        assert res.valid is True and res.plan == "dev"

    async def test_devmode_ignored_in_release(self, monkeypatch, tmp_path):
        monkeypatch.setattr(lic_mod.settings, "AP_DEVMODE", "1")
        monkeypatch.setenv("AUTOMATIZA_RELEASE", "1")
        # En release, DEVMODE no aplica: sin licencia/servidor → inválida.
        monkeypatch.setattr(lic_mod, "LICENSE_FILE", tmp_path / "license.json")
        res = await validate_license()
        assert res.valid is False
