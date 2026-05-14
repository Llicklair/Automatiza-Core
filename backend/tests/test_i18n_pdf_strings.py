"""Tests de internacionalización de strings PDF (I18N.PDF)."""
import pytest

from app.i18n import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    get_locale_or_default,
    translate,
)
from app.i18n.pdf_strings import known_keys


class TestGetLocaleOrDefault:
    def test_none_devuelve_default(self):
        assert get_locale_or_default(None) == "es"

    def test_string_vacio_devuelve_default(self):
        assert get_locale_or_default("") == "es"

    def test_locale_soportado(self):
        for loc in SUPPORTED_LOCALES:
            assert get_locale_or_default(loc) == loc

    def test_locale_con_region(self):
        # "es-ES" → "es", "en-US" → "en"
        assert get_locale_or_default("es-ES") == "es"
        assert get_locale_or_default("en-US") == "en"
        assert get_locale_or_default("ca_ES") == "ca"

    def test_locale_uppercase(self):
        assert get_locale_or_default("ES") == "es"
        assert get_locale_or_default("EN") == "en"

    def test_no_soportado_fallback_default(self):
        assert get_locale_or_default("zh") == "es"
        assert get_locale_or_default("fr") == "es"


class TestTranslate:
    def test_existe_en_es(self):
        assert translate("invoice.title", "es") == "Factura"
        assert translate("payroll.title", "es") == "Nómina"

    def test_existe_en_en(self):
        assert translate("invoice.title", "en") == "Invoice"
        assert translate("payroll.net_salary", "en") == "Net pay"

    def test_stub_ca_tiene_prefijo(self):
        out = translate("invoice.title", "ca")
        assert out.startswith("[CA] ")
        assert "Factura" in out

    def test_stub_eu_tiene_prefijo(self):
        out = translate("payroll.title", "eu")
        assert out.startswith("[EU] ")

    def test_stub_gl_tiene_prefijo(self):
        out = translate("receipt.title", "gl")
        assert out.startswith("[GL] ")

    def test_key_inexistente_devuelve_missing(self):
        assert translate("does.not.exist", "es") == "[missing:does.not.exist]"
        assert translate("does.not.exist", "en") == "[missing:does.not.exist]"

    def test_locale_none_usa_default(self):
        assert translate("invoice.title", None) == "Factura"

    def test_locale_invalido_usa_default(self):
        assert translate("invoice.title", "zh") == "Factura"

    def test_no_lanza_nunca(self):
        # Cualquier combinación de inputs raros debe devolver string.
        for args in [
            ("", ""),
            ("a", None),
            ("invoice.title", "weird-locale"),
        ]:
            result = translate(*args)
            assert isinstance(result, str)


class TestCoverage:
    """Verifica que las locales no-stub tengan todas las keys del default."""

    def test_es_es_la_fuente_completa(self):
        # Por construcción, `es` define todas las keys.
        assert len(known_keys()) > 0
        for k in known_keys():
            assert translate(k, "es") != f"[missing:{k}]"

    def test_en_cubre_todas_las_keys(self):
        """`en` se mantiene en paridad con `es` — sin missing."""
        for k in known_keys():
            t = translate(k, "en")
            assert not t.startswith("[missing:"), f"en falta key: {k}"

    def test_stubs_cubren_todas_las_keys(self):
        """CA/EU/GL stubs deben cubrir todas las keys de es (con prefijo)."""
        for stub in ("ca", "eu", "gl"):
            for k in known_keys():
                t = translate(k, stub)
                assert not t.startswith("[missing:"), f"{stub} falta key: {k}"
                # Y debe llevar el prefijo del stub
                assert t.startswith(f"[{stub.upper()}] "), (
                    f"{stub} key {k} sin prefijo: {t}"
                )
