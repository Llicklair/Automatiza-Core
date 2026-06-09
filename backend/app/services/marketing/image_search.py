"""Búsqueda de imágenes de stock vía Unsplash API."""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_UNSPLASH_URL = "https://api.unsplash.com/search/photos"


async def search_image(query: str) -> str | None:
    """Devuelve la URL de la primera imagen relevante de Unsplash, o None si no hay key."""
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
