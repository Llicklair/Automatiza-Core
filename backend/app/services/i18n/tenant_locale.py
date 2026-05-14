"""Resolución de locale por tenant para PDFs y emails (I18N.PDF).

La preferencia de idioma del cliente vive HOY como cookie del navegador
(I18N.SEL). El backend no tiene persistencia per-tenant todavía. Este
módulo encapsula la lookup para que cuando se añada la columna real
sea un cambio interno transparente al caller.

Mientras no hay BD persistente del locale:
  - `get_tenant_locale(db, tenant_id)` devuelve el default `es`.
  - El locale efectivo se inyecta vía el header `Accept-Language` del
    request, o explícito en el endpoint (`?locale=ca`).

Cuando exista `tenant_preferences.locale` (follow-up planificado en BD):
  - `get_tenant_locale()` leerá esa columna.
  - El cookie sigue ganando si el usuario logado quiere ver otra cosa.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.i18n.pdf_strings import DEFAULT_LOCALE, get_locale_or_default

Locale = Literal["es", "ca", "eu", "gl", "en"]


async def get_tenant_locale(
    db: AsyncSession,  # noqa: ARG001 — reservado para cuando exista BD
    *,
    tenant_id: UUID,  # noqa: ARG001
) -> Locale:
    """Devuelve el locale persistido del tenant. Hoy: siempre default.

    TODO follow-up: columna `tenants.locale` o tabla `tenant_preferences`
    (~0.5d). Sin BD, devolver el default `es` es semántica segura — la
    UI ofrece selector cookie (I18N.SEL) que sí persiste por device.
    """
    return DEFAULT_LOCALE  # type: ignore[return-value]


def resolve_locale(
    *,
    explicit: str | None = None,
    cookie: str | None = None,
    accept_language: str | None = None,
    tenant_default: str = DEFAULT_LOCALE,
) -> Locale:
    """Cascada de resolución del locale efectivo para un request concreto.

    Orden de precedencia (consenso Ronda 33):
      1. `explicit` — parámetro `?locale=` del endpoint (override admin).
      2. `cookie` — preferencia del usuario logado (I18N.SEL).
      3. Primer valor de `Accept-Language` que esté soportado.
      4. `tenant_default` — fallback al locale del tenant (hoy: `es`).
    """
    for raw in (explicit, cookie):
        loc = get_locale_or_default(raw)
        if raw and loc == get_locale_or_default(raw):
            # Solo aceptamos si efectivamente coincide con un soportado.
            if raw.lower().split("-")[0].split("_")[0] in {"es", "ca", "eu", "gl", "en"}:
                return loc  # type: ignore[return-value]

    # Accept-Language puede traer múltiples ("es-ES, en;q=0.9").
    if accept_language:
        for part in accept_language.split(","):
            tag = part.split(";")[0].strip()
            if not tag:
                continue
            loc = get_locale_or_default(tag)
            base = tag.lower().split("-")[0].split("_")[0]
            if base in {"es", "ca", "eu", "gl", "en"}:
                return loc  # type: ignore[return-value]

    return get_locale_or_default(tenant_default)  # type: ignore[return-value]
