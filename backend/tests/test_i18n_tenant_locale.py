"""Tests del resolver de locale por tenant (I18N.PDF wiring)."""
from uuid import uuid4

import pytest

from app.services.i18n.tenant_locale import (
    get_tenant_locale,
    resolve_locale,
)


@pytest.mark.asyncio
async def test_get_tenant_locale_devuelve_default(db, seed_tenant_and_user):
    """Hoy `get_tenant_locale` siempre devuelve `es` (sin BD persistente)."""
    tenant, _u, _t = seed_tenant_and_user
    loc = await get_tenant_locale(db, tenant_id=tenant.id)
    assert loc == "es"


@pytest.mark.asyncio
async def test_get_tenant_locale_tenant_inexistente_devuelve_default(db):
    """Aún sin tenant válido el helper no lanza — devuelve default."""
    loc = await get_tenant_locale(db, tenant_id=uuid4())
    assert loc == "es"


class TestResolveLocale:
    def test_explicit_gana(self):
        assert resolve_locale(explicit="ca", cookie="en", accept_language="gl") == "ca"

    def test_cookie_si_no_hay_explicit(self):
        assert resolve_locale(cookie="ca") == "ca"
        assert resolve_locale(cookie="eu") == "eu"

    def test_accept_language_si_no_cookie(self):
        assert resolve_locale(accept_language="ca-ES") == "ca"
        assert resolve_locale(accept_language="en-US,en;q=0.9") == "en"

    def test_accept_language_primer_soportado(self):
        # zh no soportado → fallback a en.
        assert resolve_locale(accept_language="zh-CN, en;q=0.9, es;q=0.5") == "en"

    def test_accept_language_solo_no_soportado(self):
        # Solo zh → cae a tenant_default (es).
        assert resolve_locale(accept_language="zh") == "es"

    def test_tenant_default(self):
        assert resolve_locale(tenant_default="ca") == "ca"

    def test_sin_inputs_devuelve_es(self):
        assert resolve_locale() == "es"

    def test_explicit_invalido_cae_al_siguiente(self):
        """Si explicit no es válido, se ignora y se prueba cookie."""
        assert resolve_locale(explicit="bogus", cookie="ca") == "ca"

    def test_cookie_invalida_cae_accept_language(self):
        assert resolve_locale(cookie="bogus", accept_language="eu-ES") == "eu"

    def test_todos_invalidos_cae_default(self):
        assert resolve_locale(
            explicit="bogus", cookie="x", accept_language="zh",
            tenant_default="es",
        ) == "es"


def test_invoice_lines_table_acepta_locale():
    """Smoke: el helper de _invoice_sections acepta `locale` y no lanza."""
    from app.services.documents._pdf_base import REPORTLAB_AVAILABLE
    if not REPORTLAB_AVAILABLE:
        pytest.skip("reportlab no disponible en test env")
    from reportlab.lib.styles import getSampleStyleSheet
    from app.services.pdf._invoice_sections import _invoice_lines_table

    styles = getSampleStyleSheet()
    header_sty = styles["Normal"]
    body_sty = styles["Normal"]
    right_sty = styles["Normal"]
    lines = [{"description": "Servicio X", "quantity": 1, "unit_price": 100}]
    # Debe construirse sin lanzar para `es` y `en`.
    tbl_es = _invoice_lines_table(lines, header_sty, body_sty, right_sty, {}, locale="es")
    tbl_en = _invoice_lines_table(lines, header_sty, body_sty, right_sty, {}, locale="en")
    assert tbl_es is not None
    assert tbl_en is not None
