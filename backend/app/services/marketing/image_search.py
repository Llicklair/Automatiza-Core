"""Búsqueda de imágenes de stock vía Unsplash API."""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_UNSPLASH_URL = "https://api.unsplash.com/search/photos"


async def search_image(query: str) -> str | None:
    """Devuelve la URL de una imagen de stock relevante, o None.

    Prioridad: proxy de Render (la key de Unsplash vive ahí, no en el binario del
    cliente) → si no hay proxy o no devuelve nada, key local del .env (fallback).
    """
    # URL fija de fallback: el proxy (con la key en Render) debe usarse aunque la
    # capa Electron no inyecte OAUTH_PROXY_URL (sync no actualiza service-manager).
    proxy = (settings.OAUTH_PROXY_URL or "https://automatizapyme-license-server.onrender.com").rstrip("/")
    if proxy:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(f"{proxy}/images/search", params={"query": query})
            if r.status_code == 200:
                url = r.json().get("url")
                if url:
                    return url
        except Exception as e:
            logger.warning("Proxy image search failed for %r: %s", query, e)
        # proxy sin resultado o caído → intenta key local si existe

    if not settings.UNSPLASH_ACCESS_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
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
        logger.warning("Unsplash search failed for %r: %s", query, e)
    return None
