"""Búsqueda de imágenes de stock vía Unsplash API."""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_UNSPLASH_URL = "https://api.unsplash.com/search/photos"


async def search_image(query: str) -> str | None:
    """Devuelve la URL de una imagen de stock relevante, o None.

    Orden: (1) key local del .env — rápida, sin cold start. (2) proxy de Render —
    fallback para builds distribuidos donde la key se quita del binario. Así el dev
    no sufre el cold start de Render en cada imagen.
    """
    # (1) Key local (rápido)
    if settings.UNSPLASH_ACCESS_KEY:
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                r = await client.get(
                    _UNSPLASH_URL,
                    params={"query": query, "per_page": 1, "orientation": "landscape"},
                    headers={"Authorization": f"Client-ID {settings.UNSPLASH_ACCESS_KEY}"},
                )
            if r.status_code == 200:
                results = r.json().get("results", [])
                if results:
                    return results[0]["urls"]["regular"]
        except Exception as e:
            logger.warning("Unsplash (local) failed for %r: %s", query, e)

    # (2) Proxy de Render (la key vive ahí). URL fija: no depende de que la capa
    # Electron inyecte OAUTH_PROXY_URL.
    proxy = (settings.OAUTH_PROXY_URL or "https://automatizapyme-license-server.onrender.com").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            r = await client.get(f"{proxy}/images/search", params={"query": query})
        if r.status_code == 200:
            url = r.json().get("url")
            if url:
                return url
    except Exception as e:
        logger.warning("Proxy image search failed for %r: %s", query, e)
    return None
