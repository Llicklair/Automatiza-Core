"""Tests del cliente HTTPS Backblaze B2 (BAK.B2 transport)."""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.services.backup import b2_client


def _resp(status: int = 200, json_data: dict | None = None, content: bytes = b"") -> MagicMock:
    """Mock de httpx.Response con la API que usa el cliente."""
    r = MagicMock()
    r.status_code = status
    r.json = MagicMock(return_value=json_data or {})
    r.content = content
    return r


def _client_mock() -> MagicMock:
    """Mock de httpx.AsyncClient con `get` y `post` como AsyncMock."""
    c = MagicMock()
    c.get = AsyncMock()
    c.post = AsyncMock()
    return c


@pytest.mark.asyncio
class TestAuthorize:
    async def test_devuelve_session_si_200(self):
        client = _client_mock()
        client.get.return_value = _resp(json_data={
            "apiUrl": "https://api999.backblazeb2.com",
            "downloadUrl": "https://f001.backblazeb2.com",
            "authorizationToken": "tok-abc",
        })
        creds = b2_client.B2Credentials(
            key_id="k", application_key="s", bucket_id="b", bucket_name="bk",
        )

        session = await b2_client.authorize(creds, http_client=client)

        assert session.api_url.startswith("https://api")
        assert session.auth_token == "tok-abc"
        # Auth header Basic key:secret en base64
        called_headers = client.get.call_args.kwargs["headers"]
        assert called_headers["Authorization"].startswith("Basic ")

    async def test_lanza_si_status_no_200(self):
        client = _client_mock()
        client.get.return_value = _resp(status=401, json_data={"code": "bad_auth"})
        creds = b2_client.B2Credentials(
            key_id="k", application_key="s", bucket_id="b", bucket_name="bk",
        )

        with pytest.raises(b2_client.B2Error, match="status=401"):
            await b2_client.authorize(creds, http_client=client)

    async def test_error_no_contiene_credenciales(self):
        client = _client_mock()
        client.get.return_value = _resp(status=403)
        creds = b2_client.B2Credentials(
            key_id="super-secret-key",
            application_key="super-secret-app",
            bucket_id="b", bucket_name="bk",
        )

        try:
            await b2_client.authorize(creds, http_client=client)
        except b2_client.B2Error as e:
            msg = str(e)
            assert "super-secret-key" not in msg
            assert "super-secret-app" not in msg


@pytest.mark.asyncio
class TestGetUploadUrl:
    async def test_devuelve_tuple(self):
        client = _client_mock()
        client.post.return_value = _resp(json_data={
            "uploadUrl": "https://pod-XXX.backblazeb2.com/upload",
            "authorizationToken": "ut-token",
        })
        session = b2_client.B2Session(
            api_url="https://api999.backblazeb2.com",
            download_url="https://f001.backblazeb2.com",
            auth_token="tok",
        )

        url, token = await b2_client.get_upload_url(session, "bucket-id", http_client=client)
        assert url.endswith("/upload")
        assert token == "ut-token"


@pytest.mark.asyncio
class TestUploadFile:
    async def test_envia_sha1_y_metadata(self):
        client = _client_mock()
        client.post.return_value = _resp(json_data={"fileId": "f-1", "fileName": "x.bak"})

        result = await b2_client.upload_file(
            upload_url="https://upload",
            upload_auth_token="t",
            file_name="x.bak",
            blob=b"hello world",
            http_client=client,
        )

        assert result["fileId"] == "f-1"
        headers = client.post.call_args.kwargs["headers"]
        # SHA-1 de "hello world"
        assert headers["X-Bz-Content-Sha1"] == "2aae6c35c94fcfb415dbe95f408b9ce91ee846ed"
        assert headers["X-Bz-File-Name"] == "x.bak"
        assert headers["Content-Length"] == "11"


@pytest.mark.asyncio
class TestListAndDownload:
    async def test_list_devuelve_lista_files(self):
        client = _client_mock()
        client.post.return_value = _resp(json_data={
            "files": [
                {"fileId": "f1", "fileName": "a.bak"},
                {"fileId": "f2", "fileName": "b.bak"},
            ],
        })
        session = b2_client.B2Session(
            api_url="https://api", download_url="https://dl", auth_token="t",
        )

        files = await b2_client.list_file_names(session, "bk", http_client=client)
        assert len(files) == 2
        assert files[0]["fileName"] == "a.bak"

    async def test_list_pasa_prefix_en_payload(self):
        client = _client_mock()
        client.post.return_value = _resp(json_data={"files": []})
        session = b2_client.B2Session(
            api_url="https://api", download_url="https://dl", auth_token="t",
        )

        await b2_client.list_file_names(session, "bk", prefix="tenant-xyz/", http_client=client)
        payload = client.post.call_args.kwargs["json"]
        assert payload["prefix"] == "tenant-xyz/"

    async def test_download_devuelve_content(self):
        client = _client_mock()
        client.get.return_value = _resp(content=b"encrypted-blob")
        session = b2_client.B2Session(
            api_url="https://api", download_url="https://dl", auth_token="t",
        )

        data = await b2_client.download_file_by_name(
            session, "bk", "test.bak", http_client=client,
        )
        assert data == b"encrypted-blob"


@pytest.mark.asyncio
class TestDeleteFileVersion:
    async def test_no_lanza_si_200(self):
        client = _client_mock()
        client.post.return_value = _resp(json_data={})
        session = b2_client.B2Session(
            api_url="https://api", download_url="https://dl", auth_token="t",
        )

        await b2_client.delete_file_version(session, "f1", "x.bak", http_client=client)
        client.post.assert_awaited_once()


@pytest.mark.asyncio
class TestRetry:
    async def test_retry_devuelve_resultado_si_exito_tras_fallos(self):
        attempts = {"n": 0}

        async def flaky():
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise b2_client.B2Error("transient")
            return "ok"

        result = await b2_client.with_retry(flaky, retries=5, base_delay=0.01)
        assert result == "ok"
        assert attempts["n"] == 3

    async def test_retry_agota_y_lanza(self):
        async def always_fail():
            raise b2_client.B2Error("nope")

        with pytest.raises(b2_client.B2Error, match="nope"):
            await b2_client.with_retry(always_fail, retries=2, base_delay=0.01)


@pytest.mark.asyncio
class TestUploadEncrypted:
    async def test_cifra_y_sube(self, monkeypatch):
        """End-to-end: el blob subido NO contiene el plaintext."""
        client = _client_mock()
        client.get.return_value = _resp(json_data={
            "apiUrl": "https://api999.backblazeb2.com",
            "downloadUrl": "https://f001.backblazeb2.com",
            "authorizationToken": "tok",
        })
        # get_upload_url + upload_file ambos van por .post
        client.post.side_effect = [
            _resp(json_data={
                "uploadUrl": "https://upload",
                "authorizationToken": "ut",
            }),
            _resp(json_data={"fileId": "f-99", "fileName": "x.enc"}),
        ]

        creds = b2_client.B2Credentials(
            key_id="k", application_key="s", bucket_id="b-id", bucket_name="bk",
        )
        plaintext = b"datos super secretos del cliente"
        result = await b2_client.upload_encrypted(
            plaintext=plaintext, password="pass-fuerte-x",
            file_name="tenant-1/2026-05-15.enc",
            creds=creds, http_client=client,
        )

        assert result["fileId"] == "f-99"
        # El segundo .post es el upload; capturamos su `content=` y verificamos
        # que NO contiene el plaintext (estaría cifrado).
        upload_call = client.post.call_args_list[1]
        sent_blob = upload_call.kwargs["content"]
        assert sent_blob != plaintext
        assert plaintext not in sent_blob  # plaintext no aparece literal


@pytest.mark.asyncio
class TestDownloadAndDecrypt:
    async def test_descarga_y_descifra_roundtrip(self):
        from app.services.backup.crypto import encrypt_e2e

        plaintext = b"contenido restaurado"
        password = "pass-roundtrip"
        ciphertext = encrypt_e2e(plaintext, password)

        client = _client_mock()
        client.get.side_effect = [
            _resp(json_data={
                "apiUrl": "https://api",
                "downloadUrl": "https://dl",
                "authorizationToken": "tok",
            }),
            _resp(content=ciphertext),
        ]

        creds = b2_client.B2Credentials(
            key_id="k", application_key="s", bucket_id="b", bucket_name="bk",
        )
        restored = await b2_client.download_and_decrypt(
            file_name="x.enc", password=password, creds=creds, http_client=client,
        )

        assert restored == plaintext
