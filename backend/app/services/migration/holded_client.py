"""Cliente HTTP paginado para Holded API (MIG.2).

Capa de transporte que envuelve `httpx` para llamar a la API REST de
Holded con la API key del cliente y paginar todos los recursos hasta
agotarlos. La normalización a `ImportRow` la hace `holded_importer.py`.

Diseño:
- **Async iterators** `iter_contacts()` / `iter_invoices()` que yieldean
  página a página → consumidor decide si parar (modo preview = 1 página,
  modo commit = todas).
- **Rate limit consciencia**: si Holded devuelve 429, espera el
  `Retry-After` y reintenta. Sin esto, una migración grande puede ser
  rechazada a media descarga.
- **Errores tipados** (`HoldedAuthError`, `HoldedRateLimitError`,
  `HoldedError`) — el wizard frontend muestra mensaje específico.
- **No persiste estado**: cada llamada es independiente. La sesión
  HTTP `httpx.AsyncClient` se inyecta para tests.

Ejemplo:
    creds = HoldedCredentials(api_key=user_provided_key)
    async with httpx.AsyncClient() as client:
        async for page in iter_contacts(creds, http_client=client):
            for contact_raw in page:
                row = normalize_holded_contact(contact_raw)
                ...
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator

import httpx

from app.services.migration.holded_importer import (
    HOLDED_BASE_URL,
    HoldedCredentials,
)

logger = logging.getLogger("migration.holded_client")

_DEFAULT_TIMEOUT = 30.0
_DEFAULT_PAGE_SIZE = 100  # Holded acepta hasta ~500, pero 100 da mejor latencia


class HoldedError(RuntimeError):
    """Error genérico del cliente. NO incluye la API key."""


class HoldedAuthError(HoldedError):
    """Credenciales inválidas (401 Unauthorized)."""


class HoldedRateLimitError(HoldedError):
    """429 Too Many Requests — el caller debería pausar."""


def _headers(creds: HoldedCredentials) -> dict[str, str]:
    return {"key": creds.api_key, "Accept": "application/json"}


async def _get_page(
    *,
    creds: HoldedCredentials,
    path: str,
    page: int,
    page_size: int,
    http_client: httpx.AsyncClient,
) -> list[dict[str, Any]]:
    """GET paginado. Devuelve la lista de items de la página."""
    url = f"{creds.base_url}{path}"
    params = {"page": page, "per_page": page_size}

    resp = await http_client.get(
        url, params=params, headers=_headers(creds), timeout=_DEFAULT_TIMEOUT,
    )

    if resp.status_code == 401:
        raise HoldedAuthError(
            "Holded rechazó la API key. Genera una nueva en tu panel Holded "
            "(Configuración → Desarrolladores) y vuelve a intentar."
        )
    if resp.status_code == 429:
        retry_after = resp.headers.get("Retry-After", "60")
        raise HoldedRateLimitError(
            f"Rate limit Holded — esperar {retry_after}s antes de reintentar."
        )
    if resp.status_code != 200:
        raise HoldedError(f"Holded status={resp.status_code} path={path}")

    payload = resp.json()
    # Holded a veces devuelve `{items: [...], total: N}` y a veces lista plana.
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return list(payload.get("items") or payload.get("data") or [])
    return []


async def _iter_paginated(
    *,
    creds: HoldedCredentials,
    path: str,
    page_size: int = _DEFAULT_PAGE_SIZE,
    max_pages: int | None = None,
    http_client: httpx.AsyncClient,
) -> AsyncIterator[list[dict[str, Any]]]:
    """Itera por todas las páginas hasta encontrar una vacía o llegar a max_pages.

    Maneja rate limit con back-off automático (espera Retry-After y reintenta
    la misma página hasta 3 veces antes de propagar la excepción).
    """
    page = 1
    while True:
        if max_pages is not None and page > max_pages:
            return

        attempts = 0
        while True:
            try:
                items = await _get_page(
                    creds=creds, path=path, page=page, page_size=page_size,
                    http_client=http_client,
                )
                break
            except HoldedRateLimitError as e:
                attempts += 1
                if attempts > 3:
                    raise
                # Extraer segundos del mensaje y respetar el back-off.
                delay = 60.0
                try:
                    delay = float(str(e).split("esperar ", 1)[1].split("s", 1)[0])
                except (IndexError, ValueError):
                    pass
                logger.warning(
                    "Rate limit Holded page=%d attempt=%d, esperando %.0fs",
                    page, attempts, delay,
                )
                await asyncio.sleep(min(delay, 120.0))

        if not items:
            return
        yield items
        if len(items) < page_size:
            # Última página parcial — no hay más.
            return
        page += 1


async def iter_contacts(
    creds: HoldedCredentials,
    *,
    page_size: int = _DEFAULT_PAGE_SIZE,
    max_pages: int | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> AsyncIterator[list[dict[str, Any]]]:
    """Itera todas las páginas de contactos del cliente Holded."""
    async def _run(client: httpx.AsyncClient):
        async for page in _iter_paginated(
            creds=creds, path="/contacts",
            page_size=page_size, max_pages=max_pages,
            http_client=client,
        ):
            yield page

    if http_client is not None:
        async for page in _run(http_client):
            yield page
        return
    async with httpx.AsyncClient() as client:
        async for page in _run(client):
            yield page


async def iter_invoices(
    creds: HoldedCredentials,
    *,
    page_size: int = _DEFAULT_PAGE_SIZE,
    max_pages: int | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> AsyncIterator[list[dict[str, Any]]]:
    """Itera todas las páginas de facturas emitidas del cliente Holded."""
    async def _run(client: httpx.AsyncClient):
        async for page in _iter_paginated(
            creds=creds, path="/documents/invoice",
            page_size=page_size, max_pages=max_pages,
            http_client=client,
        ):
            yield page

    if http_client is not None:
        async for page in _run(http_client):
            yield page
        return
    async with httpx.AsyncClient() as client:
        async for page in _run(client):
            yield page


async def fetch_all_contacts(
    creds: HoldedCredentials,
    *,
    max_pages: int | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> list[dict[str, Any]]:
    """Helper: descarga TODOS los contactos en una lista. Usar con cuidado."""
    out: list[dict[str, Any]] = []
    async for page in iter_contacts(
        creds, max_pages=max_pages, http_client=http_client,
    ):
        out.extend(page)
    return out


async def fetch_all_invoices(
    creds: HoldedCredentials,
    *,
    max_pages: int | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> list[dict[str, Any]]:
    """Helper: descarga TODAS las facturas en una lista."""
    out: list[dict[str, Any]] = []
    async for page in iter_invoices(
        creds, max_pages=max_pages, http_client=http_client,
    ):
        out.extend(page)
    return out
