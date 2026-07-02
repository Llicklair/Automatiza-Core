"""Strings i18n para PDFs (factura, nómina, recibo, modelos AEAT).

Diseño consensuado en Ronda 28 §52:

- **Lookup por dict** (no gettext). Menos infraestructura. La cantidad
  de strings de PDF es acotada (~50 keys), no justifica `.po`/`.mo`.
- **Fallback cascada**: si la key no existe en el locale pedido, se
  intenta `es`. Si tampoco, se devuelve `[missing:KEY]`.
- **Stubs CA/EU/GL** marcados con prefijo `[CA] /[EU] /[GL] ` hasta que
  la agencia los rellene (I18N.TR / DEC.11).

Cualquier dev que añada un string a un PDF debe:
  1. Añadir la key a `_TRANSLATIONS["es"]`.
  2. Ejecutar `python -m app.i18n.fill_stubs` para regenerar stubs.
  3. PR con el cambio.
"""

from __future__ import annotations

from typing import Literal

Locale = Literal["es", "ca", "eu", "gl", "en"]

SUPPORTED_LOCALES: tuple[Locale, ...] = ("es", "ca", "eu", "gl", "en")
DEFAULT_LOCALE: Locale = "es"


# Catálogo de strings — fuente de verdad en `es`. Las otras locales se
# generan o traducen a partir de aquí. Las keys siguen el patrón
# `<dominio>.<seccion>.<concepto>` para facilitar grep + agrupación.
_TRANSLATIONS: dict[Locale, dict[str, str]] = {
    "es": {
        # Factura
        "invoice.title": "Factura",
        "invoice.number": "Número",
        "invoice.date": "Fecha",
        "invoice.due_date": "Vencimiento",
        "invoice.issuer": "Emisor",
        "invoice.client": "Cliente",
        "invoice.nif": "NIF/CIF",
        "invoice.address": "Dirección",
        "invoice.concept": "Concepto",
        "invoice.quantity": "Cantidad",
        "invoice.unit_price": "Precio unitario",
        "invoice.discount": "Descuento",
        "invoice.tax_base": "Base imponible",
        "invoice.tax_rate": "Tipo IVA",
        "invoice.tax_amount": "Cuota IVA",
        "invoice.total": "Total",
        "invoice.irpf": "Retención IRPF",
        "invoice.payment_method": "Método de pago",
        "invoice.notes": "Notas",
        "invoice.terms": "Condiciones",
        "invoice.verifactu_hash": "Huella Verifactu",
        "invoice.verifactu_verify": "Verifica esta factura en",
        # Nómina
        "payroll.title": "Nómina",
        "payroll.period": "Período de liquidación",
        "payroll.employee": "Trabajador",
        "payroll.company": "Empresa",
        "payroll.accruals": "Devengos",
        "payroll.deductions": "Deducciones",
        "payroll.base_salary": "Salario base",
        "payroll.complements": "Complementos",
        "payroll.overtime": "Horas extras",
        "payroll.gross_total": "Total devengado",
        "payroll.social_security": "Cotización Seguridad Social",
        "payroll.irpf_withholding": "Retención IRPF",
        "payroll.other_deductions": "Otras deducciones",
        "payroll.net_salary": "Líquido a percibir",
        "payroll.signature_employee": "Firma del trabajador",
        "payroll.signature_company": "Firma de la empresa",
        # Recibo / generales
        "receipt.title": "Recibo",
        "receipt.received_from": "Recibido de",
        "receipt.amount_in_words": "Importe en letras",
        "receipt.place_date": "En, a",
        # Footer común
        "footer.page": "Página",
        "footer.of": "de",
        "footer.generated_by": "Generado por AutomatizaCore",
    },
    # CA/EU/GL: stubs con prefijo. Se rellenarán via I18N.TR.
    "ca": {},
    "eu": {},
    "gl": {},
    "en": {
        "invoice.title": "Invoice",
        "invoice.number": "Number",
        "invoice.date": "Date",
        "invoice.due_date": "Due date",
        "invoice.issuer": "Issuer",
        "invoice.client": "Customer",
        "invoice.nif": "Tax ID",
        "invoice.address": "Address",
        "invoice.concept": "Description",
        "invoice.quantity": "Quantity",
        "invoice.unit_price": "Unit price",
        "invoice.discount": "Discount",
        "invoice.tax_base": "Taxable base",
        "invoice.tax_rate": "VAT rate",
        "invoice.tax_amount": "VAT amount",
        "invoice.total": "Total",
        "invoice.irpf": "Income tax withholding",
        "invoice.payment_method": "Payment method",
        "invoice.notes": "Notes",
        "invoice.terms": "Terms",
        "invoice.verifactu_hash": "Verifactu fingerprint",
        "invoice.verifactu_verify": "Verify this invoice at",
        "payroll.title": "Payslip",
        "payroll.period": "Pay period",
        "payroll.employee": "Employee",
        "payroll.company": "Company",
        "payroll.accruals": "Accruals",
        "payroll.deductions": "Deductions",
        "payroll.base_salary": "Base salary",
        "payroll.complements": "Complements",
        "payroll.overtime": "Overtime",
        "payroll.gross_total": "Gross total",
        "payroll.social_security": "Social Security contributions",
        "payroll.irpf_withholding": "Income tax withholding",
        "payroll.other_deductions": "Other deductions",
        "payroll.net_salary": "Net pay",
        "payroll.signature_employee": "Employee signature",
        "payroll.signature_company": "Company signature",
        "receipt.title": "Receipt",
        "receipt.received_from": "Received from",
        "receipt.amount_in_words": "Amount in words",
        "receipt.place_date": "On, at",
        "footer.page": "Page",
        "footer.of": "of",
        "footer.generated_by": "Generated by AutomatizaCore",
    },
}

# Generar stubs CA/EU/GL en import-time con prefijo legible.
for _stub_locale, _prefix in (("ca", "[CA] "), ("eu", "[EU] "), ("gl", "[GL] ")):
    _TRANSLATIONS[_stub_locale] = {  # type: ignore[index]
        k: _prefix + v for k, v in _TRANSLATIONS["es"].items()
    }


def get_locale_or_default(raw: str | None) -> Locale:
    """Normaliza un string de locale al canon. Fallback `es`."""
    if not raw:
        return DEFAULT_LOCALE
    raw_lower = raw.lower().split("-")[0].split("_")[0]
    if raw_lower in SUPPORTED_LOCALES:
        return raw_lower
    return DEFAULT_LOCALE


def translate(key: str, locale: str | None = None) -> str:
    """Devuelve la traducción para `key` en `locale`.

    Cascada: locale pedido → es → `[missing:KEY]` (visualmente auditable).
    Nunca lanza.
    """
    loc = get_locale_or_default(locale)
    table = _TRANSLATIONS.get(loc) or {}
    if key in table:
        return table[key]
    # Fallback al default.
    if key in _TRANSLATIONS[DEFAULT_LOCALE]:
        return _TRANSLATIONS[DEFAULT_LOCALE][key]
    return f"[missing:{key}]"


def known_keys() -> set[str]:
    """Conjunto de keys conocidas (definidas al menos en `es`)."""
    return set(_TRANSLATIONS[DEFAULT_LOCALE].keys())
