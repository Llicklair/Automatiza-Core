"""Tests de endurecimiento de licencia: middleware fail-closed + sin bypass."""
import base64
import json
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.core import license as lic_mod
from app.core.license import cached_license_state, save_license, validate_license
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


def _install_test_keypair(monkeypatch) -> Ed25519PrivateKey:
    """Sustituye la clave pública embebida por una de test y devuelve su privada,
    para poder fabricar grants firmados como lo haría el servidor real."""
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    from cryptography.hazmat.primitives import serialization

    raw_pub = pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    monkeypatch.setattr(lic_mod, "_PUBLIC_KEY_B64", base64.b64encode(raw_pub).decode())
    return priv


def _grant(priv: Ed25519PrivateKey, key, machine_id, issued_at, plan) -> str:
    return base64.b64encode(priv.sign(f"{key}:{machine_id}:{issued_at}:{plan}".encode())).decode()


@pytest.mark.asyncio
class TestForgedCacheRejected:
    """El vector crítico: caché con HMAC auto-firmado pero SIN grant del servidor.

    El HMAC usa el machine_id como clave —público para quien lee el código—, así
    que un atacante puede fabricar una firma HMAC válida. El grant Ed25519 es lo
    que NO puede falsificar sin la clave privada del servidor.
    """

    async def test_cache_forjada_sin_grant_es_invalida(self, monkeypatch, tmp_path):
        monkeypatch.setattr(lic_mod, "LICENSE_FILE", tmp_path / "license.json")
        _install_test_keypair(monkeypatch)
        # El atacante escribe una caché "válida" a mano: HMAC bien calculado
        # (conoce el esquema y su machine_id), fecha de hoy, plan pro... pero SIN
        # grant firmado por el servidor.
        save_license("AP-P-ROBADA", "pro")  # save_license deja grant_sig=""
        # Offline (servidor caído): antes esto concedía acceso; ahora NO.
        monkeypatch.setattr(lic_mod, "LICENSE_SERVER", "http://127.0.0.1:9")  # inalcanzable
        res = await validate_license()
        assert res.valid is False
        assert cached_license_state().valid is False

    async def test_grant_valido_concede_offline(self, monkeypatch, tmp_path):
        monkeypatch.setattr(lic_mod, "LICENSE_FILE", tmp_path / "license.json")
        priv = _install_test_keypair(monkeypatch)
        machine_id = lic_mod.get_machine_id()
        issued_at = datetime.now(timezone.utc).isoformat()
        gsig = _grant(priv, "AP-P-REAL", machine_id, issued_at, "pro")
        save_license("AP-P-REAL", "pro", issued_at=issued_at, grant_sig=gsig)
        # Servidor caído pero grant válido y dentro de gracia → acceso offline.
        monkeypatch.setattr(lic_mod, "LICENSE_SERVER", "http://127.0.0.1:9")
        res = await validate_license()
        assert res.valid is True and res.plan == "pro"
        assert cached_license_state().valid is True

    async def test_grant_caducado_no_concede(self, monkeypatch, tmp_path):
        monkeypatch.setattr(lic_mod, "LICENSE_FILE", tmp_path / "license.json")
        priv = _install_test_keypair(monkeypatch)
        machine_id = lic_mod.get_machine_id()
        old = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        gsig = _grant(priv, "AP-P-REAL", machine_id, old, "pro")
        save_license("AP-P-REAL", "pro", issued_at=old, grant_sig=gsig)
        monkeypatch.setattr(lic_mod, "LICENSE_SERVER", "http://127.0.0.1:9")
        assert (await validate_license()).valid is False

    async def test_grant_de_otra_maquina_no_verifica(self, monkeypatch, tmp_path):
        monkeypatch.setattr(lic_mod, "LICENSE_FILE", tmp_path / "license.json")
        priv = _install_test_keypair(monkeypatch)
        issued_at = datetime.now(timezone.utc).isoformat()
        # Grant firmado para OTRO machine_id (copiar el license.json a otro equipo).
        gsig = _grant(priv, "AP-P-REAL", "machine-de-otro", issued_at, "pro")
        raw = {
            "key": "AP-P-REAL", "plan": "pro", "machine_id": lic_mod.get_machine_id(),
            "last_validated": issued_at, "issued_at": issued_at, "grant_sig": gsig,
        }
        raw["sig"] = lic_mod._sign(
            lic_mod._cache_payload(raw["key"], raw["plan"], raw["last_validated"], raw["machine_id"]),
            raw["machine_id"],
        )
        (tmp_path / "license.json").write_text(json.dumps(raw), encoding="utf-8")
        monkeypatch.setattr(lic_mod, "LICENSE_SERVER", "http://127.0.0.1:9")
        assert (await validate_license()).valid is False


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
