"""Generación de imágenes con IA vía OpenAI Images API.

Complementa `image_search` (stock de Unsplash): aquí se *crea* una imagen a medida
a partir de un prompt. Devuelve una URL pública temporal alojada por OpenAI (~2h
con dall-e-3, response_format=url), suficiente para previsualizar y publicar al
momento. Para posts programados a futuro conviene usar stock o una URL permanente.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_OPENAI_IMAGES_URL = "https://api.openai.com/v1/images/generations"


async def generate_image(prompt: str) -> str | None:
    """Genera una imagen con IA y devuelve su URL, o None si no es posible.

    Requiere `OPENAI_API_KEY`. Usa `OPENAI_IMAGE_MODEL` (por defecto dall-e-3).
    Solo se soportan modelos que devuelven URL (dall-e-2/3); los que devuelven
    base64 (p. ej. gpt-image-1) necesitarían hosting propio y no se cubren aquí.
    """
    prompt = (prompt or "").strip()
    if not prompt or not settings.OPENAI_API_KEY:
        return None

    model = settings.OPENAI_IMAGE_MODEL or "dall-e-3"
    payload: dict = {
        "model": model,
        "prompt": prompt[:1000],
        "n": 1,
        "size": "1024x1024",
    }
    if model.startswith("dall-e"):
        payload["response_format"] = "url"

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                _OPENAI_IMAGES_URL,
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                json=payload,
            )
        if r.status_code == 200:
            data = r.json().get("data", [])
            if data and data[0].get("url"):
                return data[0]["url"]
            logger.warning("OpenAI image gen sin URL (¿modelo base64?): model=%s", model)
        else:
            logger.warning("OpenAI image gen %s: %s", r.status_code, r.text[:200])
    except Exception as e:
        logger.warning("OpenAI image gen failed for %r: %s", prompt, e)
    return None
