"""Cliente HTTPS para Backblaze B2 (BAK.B2 transport).

Implementación mínima self-contained de la B2 Native API v2:
  - `b2_authorize_account` → obtiene apiUrl + authToken
  - `b2_get_upload_url`    → URL temporal para subir un archivo
  - `b2_upload_file`       → POST del binario cifrado
  - `b2_list_file_names`   → lista archivos para retención
  - `b2_download_file_by_name` → restore
  - `b2_delete_file_version` → aplicar retención (rolling 30d + 12 monthly)

Por qué no usar `b2sdk` oficial:
  - Sin dependencia extra: usa `httpx` ya en deps.
  - Stateless: cada operación pide auth nueva o reusa token.
  - Auditable: una función por endpoint, ningún wrap mágico.

Las credenciales (`B2_KEY_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_ID`,
`B2_BUCKET_NAME`) se leen del `app.core.config.settings`. El cliente
NO las loguea — sus errores omiten el authToken también.

Diseñado para que `services/backup/crypto.py:encrypt_e2e()` sea quien
cifre el blob ANTES de pasarlo a `upload_encrypted()`. El servidor de
B2 nunca ve el plaintext.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger("backup.b2_client")

_AUTHORIZE_URL = "https://api.backblazeb2.com/b2api/v2/b2_authorize_account"
_DEFAULT_TIMEOUT = 60.0


class B2Error(RuntimeError):
    """Error genérico del cliente B2 — NO incluye credenciales."""


@dataclass(frozen=True)
class B2Credentials:
    key_id: str
    application_key: str
    bucket_id: str
    bucket_name: str

    @classmethod
    def from_settings(cls) -> "B2Credentials":
        from app.core.config import settings

        for attr in ("B2_KEY_ID", "B2_APPLICATION_KEY", "B2_BUCKET_ID", "B2_BUCKET_NAME"):
            if not getattr(settings, attr, ""):
                raise B2Error(
                    f"Falta `{attr}` en settings. Configura la integración B2 "
                    "desde la UI de backup antes de usar el transporte."
                )
        return cls(
            key_id=settings.B2_KEY_ID,
            application_key=settings.B2_APPLICATION_KEY,
            bucket_id=settings.B2_BUCKET_ID,
            bucket_name=settings.B2_BUCKET_NAME,
        )


@dataclass
class B2Session:
    """Sesión autenticada — válida ~24h según docs B2."""

    api_url: str
    download_url: str
    auth_token: str


async def authorize(
    creds: B2Credentials, *, http_client: httpx.AsyncClient | None = None,
) -> B2Session:
    """Llama `b2_authorize_account` con Basic auth y devuelve la sesión."""
    basic = base64.b64encode(f"{creds.key_id}:{creds.application_key}".encode()).decode()
    headers = {"Authorization": f"Basic {basic}"}

    async def _do(client: httpx.AsyncClient) -> B2Session:
        resp = await client.get(_AUTHORIZE_URL, headers=headers, timeout=_DEFAULT_TIMEOUT)
        if resp.status_code != 200:
            raise B2Error(f"authorize_account failed status={resp.status_code}")
        data = resp.json()
        return B2Session(
            api_url=data["apiUrl"],
            download_url=data["downloadUrl"],
            auth_token=data["authorizationToken"],
        )

    if http_client is not None:
        return await _do(http_client)
    async with httpx.AsyncClient() as client:
        return await _do(client)


async def get_upload_url(
    session: B2Session, bucket_id: str,
    *, http_client: httpx.AsyncClient | None = None,
) -> tuple[str, str]:
    """Pide una URL+token temporales para hacer un upload concreto."""
    payload = {"bucketId": bucket_id}
    headers = {"Authorization": session.auth_token}

    async def _do(client: httpx.AsyncClient) -> tuple[str, str]:
        resp = await client.post(
            f"{session.api_url}/b2api/v2/b2_get_upload_url",
            json=payload, headers=headers, timeout=_DEFAULT_TIMEOUT,
        )
        if resp.status_code != 200:
            raise B2Error(f"get_upload_url failed status={resp.status_code}")
        data = resp.json()
        return data["uploadUrl"], data["authorizationToken"]

    if http_client is not None:
        return await _do(http_client)
    async with httpx.AsyncClient() as client:
        return await _do(client)


def _sha1_hex(blob: bytes) -> str:
    return hashlib.sha1(blob).hexdigest()


async def upload_file(
    *,
    upload_url: str,
    upload_auth_token: str,
    file_name: str,
    blob: bytes,
    content_type: str = "application/octet-stream",
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """POST del blob. B2 valida SHA-1 contra el header `X-Bz-Content-Sha1`."""
    headers = {
        "Authorization": upload_auth_token,
        "X-Bz-File-Name": file_name,
        "Content-Type": content_type,
        "Content-Length": str(len(blob)),
        "X-Bz-Content-Sha1": _sha1_hex(blob),
    }

    async def _do(client: httpx.AsyncClient) -> dict[str, Any]:
        resp = await client.post(
            upload_url, headers=headers, content=blob, timeout=_DEFAULT_TIMEOUT * 5,
        )
        if resp.status_code != 200:
            raise B2Error(f"upload_file failed status={resp.status_code}")
        return resp.json()

    if http_client is not None:
        return await _do(http_client)
    async with httpx.AsyncClient() as client:
        return await _do(client)


async def list_file_names(
    session: B2Session, bucket_id: str,
    *, prefix: str = "", max_count: int = 100,
    http_client: httpx.AsyncClient | None = None,
) -> list[dict[str, Any]]:
    """Lista archivos del bucket — usado por la retención (BAK.B2 §6)."""
    payload = {
        "bucketId": bucket_id, "maxFileCount": max_count,
        "prefix": prefix,
    }
    headers = {"Authorization": session.auth_token}

    async def _do(client: httpx.AsyncClient) -> list[dict[str, Any]]:
        resp = await client.post(
            f"{session.api_url}/b2api/v2/b2_list_file_names",
            json=payload, headers=headers, timeout=_DEFAULT_TIMEOUT,
        )
        if resp.status_code != 200:
            raise B2Error(f"list_file_names failed status={resp.status_code}")
        return resp.json().get("files", [])

    if http_client is not None:
        return await _do(http_client)
    async with httpx.AsyncClient() as client:
        return await _do(client)


async def download_file_by_name(
    session: B2Session, bucket_name: str, file_name: str,
    *, http_client: httpx.AsyncClient | None = None,
) -> bytes:
    """Descarga un archivo. El caller descifra con `crypto.decrypt_e2e()`."""
    url = f"{session.download_url}/file/{bucket_name}/{file_name}"
    headers = {"Authorization": session.auth_token}

    async def _do(client: httpx.AsyncClient) -> bytes:
        resp = await client.get(url, headers=headers, timeout=_DEFAULT_TIMEOUT * 5)
        if resp.status_code != 200:
            raise B2Error(f"download failed status={resp.status_code}")
        return resp.content

    if http_client is not None:
        return await _do(http_client)
    async with httpx.AsyncClient() as client:
        return await _do(client)


async def delete_file_version(
    session: B2Session, file_id: str, file_name: str,
    *, http_client: httpx.AsyncClient | None = None,
) -> None:
    """Borra una versión concreta de archivo (para aplicar retención)."""
    payload = {"fileId": file_id, "fileName": file_name}
    headers = {"Authorization": session.auth_token}

    async def _do(client: httpx.AsyncClient) -> None:
        resp = await client.post(
            f"{session.api_url}/b2api/v2/b2_delete_file_version",
            json=payload, headers=headers, timeout=_DEFAULT_TIMEOUT,
        )
        if resp.status_code != 200:
            raise B2Error(f"delete failed status={resp.status_code}")

    if http_client is not None:
        await _do(http_client)
    else:
        async with httpx.AsyncClient() as client:
            await _do(client)


# ── Flujo combinado: cifrar + subir ────────────────────────────────────────

async def upload_encrypted(
    *,
    plaintext: bytes,
    password: str,
    file_name: str,
    creds: B2Credentials | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Cifra `plaintext` con AES-256-GCM via `crypto.encrypt_e2e()` y sube.

    Devuelve el dict de respuesta de `upload_file` (incluye fileId).
    El servidor B2 nunca ve el plaintext.
    """
    from app.services.backup.crypto import encrypt_e2e

    creds = creds or B2Credentials.from_settings()
    ciphertext = encrypt_e2e(plaintext, password)

    session = await authorize(creds, http_client=http_client)
    upload_url, upload_token = await get_upload_url(
        session, creds.bucket_id, http_client=http_client,
    )
    return await upload_file(
        upload_url=upload_url,
        upload_auth_token=upload_token,
        file_name=file_name,
        blob=ciphertext,
        http_client=http_client,
    )


async def download_and_decrypt(
    *,
    file_name: str,
    password: str,
    creds: B2Credentials | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> bytes:
    """Descarga y descifra. Devuelve el plaintext original."""
    from app.services.backup.crypto import decrypt_e2e

    creds = creds or B2Credentials.from_settings()
    session = await authorize(creds, http_client=http_client)
    ciphertext = await download_file_by_name(
        session, creds.bucket_name, file_name, http_client=http_client,
    )
    return decrypt_e2e(ciphertext, password)


# ── Reintentos básicos ──────────────────────────────────────────────────────

async def with_retry(
    fn, *args, retries: int = 3, base_delay: float = 1.0, **kwargs,
):
    """Reintentos exponenciales. Útil para uploads largos sobre redes pobres."""
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            return await fn(*args, **kwargs)
        except B2Error as e:
            last_err = e
            if attempt < retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "B2 retry %d/%d tras error: %s (esperando %.1fs)",
                    attempt + 1, retries, e, delay,
                )
                await asyncio.sleep(delay)
    raise last_err if last_err else B2Error("with_retry agotó intentos sin error capturado")
