"""Selección del proveedor de publicación de marketing (seam intercambiable).

Los consumidores (scheduler, rutas) llaman `get_publisher().publish_post(post, db)`
en vez de acoplarse a una implementación concreta. Hoy devuelve Zernio; cambiar de
proveedor (o volver atrás) es una sola línea aquí, sin tocar a los consumidores.
"""

from __future__ import annotations

from app.services.marketing.publisher_base import MarketingPublisher
from app.services.marketing.zernio_publisher import ZernioPublisher


def get_publisher() -> MarketingPublisher:
    """Devuelve el publisher de marketing activo."""
    return ZernioPublisher()
