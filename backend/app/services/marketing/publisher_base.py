"""Interfaz común de publicación de marketing, independiente del proveedor.

Permite intercambiar el backend de publicación (Zernio hoy; otro mañana) sin tocar
rutas, scheduler ni agentes. El proveedor concreto implementa `publish_post` con
esta firma y NUNCA lanza: actualiza el `ScheduledPost` in-place y devuelve el
resultado.
"""

from __future__ import annotations

from collections import namedtuple
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.marketing import ScheduledPost

# ok = se publicó; transient = el fallo es reintentable (rate limit / red / 5xx).
PublishResult = namedtuple("PublishResult", ["ok", "transient"])


class MarketingPublisher(Protocol):
    async def publish_post(self, post: ScheduledPost, db: AsyncSession) -> PublishResult:
        """Publica `post` y actualiza su estado en BD. No lanza excepciones."""
        ...
