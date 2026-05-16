"""Internacionalización de strings backend (I18N.PDF + futuros emails).

Patrón canónico: el caller llama `translate("invoice.label", locale)`
y obtiene la traducción. La función nunca lanza — un key desconocido
devuelve el propio key entre corchetes (auditable visualmente).

Locales soportados: `es` (default), `ca`, `eu`, `gl`, `en`. Las
traducciones CA/EU/GL son stubs hasta I18N.TR (DEC.11 agencia).
"""

from .pdf_strings import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    get_locale_or_default,
    translate,
)

__all__ = [
    "SUPPORTED_LOCALES",
    "DEFAULT_LOCALE",
    "translate",
    "get_locale_or_default",
]
