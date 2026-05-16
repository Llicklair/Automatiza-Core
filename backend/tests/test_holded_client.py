"""Tests del cliente HTTP paginado Holded (MIG.2)."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services.migration import holded_client as hc
from app.services.migration.holded_importer import HoldedCredentials


def _resp(status: int = 200, json_data=None, headers: dict | None = None) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.json = MagicMock(return_value=json_data if json_data is not None else [])
    r.headers = headers or {}
    return r


def _client_mock() -> MagicMock:
    c = MagicMock()
    c.get = AsyncMock()
    return c


def _creds() -> HoldedCredentials:
    return HoldedCredentials(api_key="test-key-do-not-leak")


@pytest.mark.asyncio
class TestGetPage:
    async def test_pasa_api_key_en_header(self):
        client = _client_mock()
        client.get.return_value = _resp(json_data=[{"id": "c1"}])

        await hc._get_page(
            creds=_creds(), path="/contacts", page=1, page_size=10,
            http_client=client,
        )

        headers = client.get.call_args.kwargs["headers"]
        assert headers["key"] == "test-key-do-not-leak"
        assert headers["Accept"] == "application/json"

    async def test_401_lanza_auth_error_sin_credencial_en_msg(self):
        client = _client_mock()
        client.get.return_value = _resp(status=401)

        with pytest.raises(hc.HoldedAuthError) as exc:
            await hc._get_page(
                creds=_creds(), path="/contacts", page=1, page_size=10,
                http_client=client,
            )
        assert "test-key-do-not-leak" not in str(exc.value)

    async def test_429_lanza_rate_limit_con_retry_after(self):
        client = _client_mock()
        client.get.return_value = _resp(status=429, headers={"Retry-After": "30"})

        with pytest.raises(hc.HoldedRateLimitError, match="30"):
            await hc._get_page(
                creds=_creds(), path="/contacts", page=1, page_size=10,
                http_client=client,
            )

    async def test_otros_status_lanzan_holded_error(self):
        client = _client_mock()
        client.get.return_value = _resp(status=500)

        with pytest.raises(hc.HoldedError, match="500"):
            await hc._get_page(
                creds=_creds(), path="/contacts", page=1, page_size=10,
                http_client=client,
            )

    async def test_acepta_payload_lista_plana(self):
        client = _client_mock()
        client.get.return_value = _resp(json_data=[{"id": "1"}, {"id": "2"}])

        items = await hc._get_page(
            creds=_creds(), path="/x", page=1, page_size=10,
            http_client=client,
        )
        assert len(items) == 2

    async def test_acepta_payload_dict_items(self):
        client = _client_mock()
        client.get.return_value = _resp(json_data={"items": [{"id": "a"}], "total": 1})

        items = await hc._get_page(
            creds=_creds(), path="/x", page=1, page_size=10,
            http_client=client,
        )
        assert len(items) == 1
        assert items[0]["id"] == "a"


@pytest.mark.asyncio
class TestPagination:
    async def test_para_cuando_pagina_vacia(self):
        client = _client_mock()
        client.get.side_effect = [
            _resp(json_data=[{"id": "1"}] * 100),
            _resp(json_data=[{"id": "2"}] * 100),
            _resp(json_data=[]),  # señal de fin
        ]

        pages = []
        async for page in hc.iter_contacts(_creds(), http_client=client):
            pages.append(page)

        assert len(pages) == 2

    async def test_para_cuando_pagina_parcial(self):
        client = _client_mock()
        client.get.side_effect = [
            _resp(json_data=[{"id": "1"}] * 100),
            _resp(json_data=[{"id": "2"}] * 47),  # < page_size → última
        ]

        pages = []
        async for page in hc.iter_contacts(_creds(), http_client=client):
            pages.append(page)

        assert len(pages) == 2
        # No debe haber hecho una 3ª llamada.
        assert client.get.call_count == 2

    async def test_respeta_max_pages(self):
        client = _client_mock()
        client.get.return_value = _resp(json_data=[{"id": "x"}] * 100)

        pages = []
        async for page in hc.iter_contacts(
            _creds(), max_pages=2, http_client=client,
        ):
            pages.append(page)

        assert len(pages) == 2

    async def test_fetch_all_aplana(self):
        client = _client_mock()
        client.get.side_effect = [
            _resp(json_data=[{"id": "1"}, {"id": "2"}]),
        ]

        all_items = await hc.fetch_all_contacts(_creds(), http_client=client)
        assert len(all_items) == 2


@pytest.mark.asyncio
class TestEndpoints:
    async def test_iter_contacts_apunta_a_contacts(self):
        client = _client_mock()
        client.get.return_value = _resp(json_data=[])

        async for _ in hc.iter_contacts(_creds(), http_client=client):
            pass

        url_called = client.get.call_args.args[0]
        assert "/contacts" in url_called

    async def test_iter_invoices_apunta_a_documents_invoice(self):
        client = _client_mock()
        client.get.return_value = _resp(json_data=[])

        async for _ in hc.iter_invoices(_creds(), http_client=client):
            pass

        url_called = client.get.call_args.args[0]
        assert "/documents/invoice" in url_called


@pytest.mark.asyncio
class TestRateLimitRetry:
    async def test_back_off_y_reintento_tras_429(self, monkeypatch):
        # Patch asyncio.sleep para no esperar de verdad
        slept = []

        async def fake_sleep(seconds):
            slept.append(seconds)

        monkeypatch.setattr("app.services.migration.holded_client.asyncio.sleep", fake_sleep)

        client = _client_mock()
        client.get.side_effect = [
            _resp(status=429, headers={"Retry-After": "5"}),
            _resp(json_data=[{"id": "1"}]),
        ]

        pages = []
        async for page in hc.iter_contacts(_creds(), http_client=client):
            pages.append(page)

        assert len(pages) == 1
        assert slept and slept[0] == 5.0

    async def test_se_rinde_tras_3_rate_limits_consecutivos(self, monkeypatch):
        async def fake_sleep(_):
            pass

        monkeypatch.setattr("app.services.migration.holded_client.asyncio.sleep", fake_sleep)

        client = _client_mock()
        client.get.return_value = _resp(status=429, headers={"Retry-After": "1"})

        with pytest.raises(hc.HoldedRateLimitError):
            async for _ in hc.iter_contacts(_creds(), http_client=client):
                pass
