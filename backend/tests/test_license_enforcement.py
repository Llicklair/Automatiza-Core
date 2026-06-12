"""Tests de endurecimiento de licencia: middleware fail-closed + sin bypass."""
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
class TestNoBypass:
    async def test_no_license_is_invalid(self, monkeypatch, tmp_path):
        # Sin licencia y sin bypass por entorno → inválida (ya no existe modo dev).
        monkeypatch.setattr(lic_mod, "LICENSE_FILE", tmp_path / "license.json")
        res = await validate_license()
        assert res.valid is False


@pytest.mark.asyncio
class TestPeriodicRevalidation:
    async def test_refresh_updates_app_state(self, monkeypatch):
        async def fake_validate():
            return lic_mod.LicenseResult(valid=True, plan="pro")

        monkeypatch.setattr(lic_mod, "validate_license", fake_validate)

        class _State:
            pass

        class _App:
            state = _State()

        app = _App()
        await lic_mod.refresh_app_license_state(app)
        assert app.state.license_valid is True
        assert app.state.license_plan == "pro"
