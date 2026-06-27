"""Tests para `_render` de email marketing.

En el CUERPO HTML (`escape_html=True`) los datos del destinatario sustituidos
deben ir HTML-escapados (correctitud HTML + defensa XSS). La plantilla en sí NO
se escapa (es HTML que el tenant escribe a propósito); solo los valores
`{{nombre}}` / `{{email}}` sustituidos.

En el ASUNTO (`escape_html=False`, por defecto) NO se escapa: el Subject es una
cabecera de texto plano y el cliente de correo no decodifica entidades HTML, así
que escaparlo mostraría `&amp;` literal.
"""

from types import SimpleNamespace

from app.services.email_marketing.sender import _render

TEMPLATE = "<p>Hola {{nombre}} (<a href='mailto:{{email}}'>{{email}}</a>)</p>"
SUBJECT = "Oferta para {{nombre}}"


def _recipient(name, email="user@example.com"):
    # `EmailCampaignRecipient` es un modelo ORM; para llamar a `_render`
    # directamente basta con un objeto con `.name` y `.email`.
    return SimpleNamespace(name=name, email=email)


# --- CUERPO HTML: escape_html=True --------------------------------------------


def test_body_escapes_script_tag():
    body = _render(TEMPLATE, _recipient("<script>alert(1)</script>"), escape_html=True)
    assert "&lt;script&gt;" in body
    assert "<script>" not in body


def test_body_escapes_ampersand():
    body = _render(TEMPLATE, _recipient("Tom & Jerry"), escape_html=True)
    assert "Tom &amp; Jerry" in body


def test_body_escapes_email_value():
    body = _render(
        TEMPLATE, _recipient("Ana", email="a&b@example.com"), escape_html=True
    )
    assert "a&amp;b@example.com" in body


def test_body_normal_name_unchanged():
    # CONTROL: caso normal no se rompe y el resto de la plantilla queda intacto.
    body = _render(TEMPLATE, _recipient("Ana", email="ana@example.com"), escape_html=True)
    assert "Hola Ana" in body
    assert "ana@example.com" in body
    # Texto/markup fijo de la plantilla intacto (no se escapó la plantilla).
    assert "<p>" in body
    assert "<a href='mailto:" in body


def test_body_none_name():
    body = _render(TEMPLATE, _recipient(None), escape_html=True)
    assert "Hola  (" in body


# --- ASUNTO (texto plano): escape_html=False (por defecto) --------------------


def test_subject_does_not_escape_ampersand():
    # El asunto NO debe HTML-escaparse: `&` permanece `&`, no `&amp;`.
    subject = _render("Tom & Jerry: {{nombre}}", _recipient("Ana & Bob"))
    assert subject == "Tom & Jerry: Ana & Bob"
    assert "&amp;" not in subject


def test_subject_substitutes_without_escaping():
    subject = _render(SUBJECT, _recipient("José <jefe>"))
    # Sustituye el placeholder pero NO escapa (Subject es texto plano).
    assert subject == "Oferta para José <jefe>"
