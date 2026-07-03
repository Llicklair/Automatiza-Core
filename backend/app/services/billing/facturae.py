"""Generador de FacturaE 3.2.2 — formato XML estándar de la AEAT para B2G/B2B."""

import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.auth import Tenant
from app.db.models.models import Invoice


class ProformaNotFiscalError(ValueError):
    """Se intentó producir una FacturaE oficial de una proforma no fiscal.

    Opción A: el ERP no emite facturas fiscales. Convertir una proforma en una
    FacturaE (XML legal + firma XAdES) la volvería indistinguible de una factura
    real ante FACe/terceros, por eso se bloquea.
    """


def is_non_fiscal_proforma(invoice_type: str | None, invoice_number: str | None) -> bool:
    """True si NO es una factura fiscal genuinamente emitida.

    Una proforma no fiscal es cualquier factura con ``invoice_type == "proforma"``
    o sin número fiscal real (None/vacío o que empieza por ``PROFORMA``). Estas
    nunca pueden convertirse en una FacturaE oficial/firmada.
    """
    if (invoice_type or "").strip().lower() == "proforma":
        return True
    num = (invoice_number or "").strip()
    return not num or num.upper().startswith("PROFORMA")


def _sub(parent: ET.Element, tag: str, text: str | None = None) -> ET.Element:
    el = ET.SubElement(parent, tag)
    if text is not None:
        el.text = text
    return el


def _fmt(n) -> str:
    return f"{float(n):.2f}"


def _amount_el(parent: ET.Element, tag: str, value) -> None:
    """Crea un elemento <tag><TotalAmount>value</TotalAmount></tag>."""
    el = _sub(parent, tag)
    _sub(el, "TotalAmount", _fmt(value))


def _build_party(
    parent: ET.Element,
    tag: str,
    nif: str,
    corp_name: str,
    address: str,
    postal_code: str,
    city: str,
) -> None:
    party = _sub(parent, tag)
    tax_id = _sub(party, "TaxIdentification")
    # CIF (empresas) = 9 chars starting with letter; NIF (personas) = 8 digits + letter
    is_person = bool(re.match(r"^\d{8}[A-Za-z]$", (nif or "").strip()))
    _sub(tax_id, "PersonTypeCode", "F" if is_person else "J")
    _sub(tax_id, "ResidenceTypeCode", "R")
    _sub(tax_id, "TaxIdentificationNumber", (nif or "").strip()[:9] or "00000000T")
    entity = _sub(party, "LegalEntity")
    _sub(entity, "CorporateName", (corp_name or "")[:80])
    addr = _sub(entity, "AddressInSpain")
    _sub(addr, "Address", (address or "")[:80])
    _sub(addr, "PostCode", (postal_code or "00000")[:5])
    _sub(addr, "Town", (city or "-")[:50])
    _sub(addr, "Province", (city or "-")[:20])
    _sub(addr, "CountryCode", "ESP")


async def generate_facturae_xml(invoice_id: UUID, tenant_id: UUID, db: AsyncSession) -> tuple[bytes, str]:
    """Genera FacturaE 3.2.2 XML para una factura emitida.
    Devuelve (xml_bytes, filename).
    """
    result = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.client), selectinload(Invoice.lines))
        .where(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise ValueError("Factura no encontrada")

    # GUARD defensa-en-profundidad (Opción A): jamás generar FacturaE de una
    # proforma no fiscal, aunque un caller directo intente saltarse la ruta.
    if is_non_fiscal_proforma(invoice.invoice_type, invoice.invoice_number):
        raise ProformaNotFiscalError(
            "No se puede generar FacturaE de una proforma: la factura debe "
            "emitirse en el sistema de facturación certificado externo."
        )

    tenant_res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        raise ValueError("Empresa no encontrada")

    client = invoice.client
    inv_num = invoice.invoice_number or str(invoice.id)[:8]
    serie_match = re.match(r"([A-Za-z]+)", inv_num)
    serie = serie_match.group(1) if serie_match else "F"
    issue_date = invoice.date.strftime("%Y-%m-%d") if invoice.date else datetime.now(tz=UTC).strftime("%Y-%m-%d")

    # ── Tax breakdown by rate ─────────────────────────────────────────────────
    tax_groups: dict[str, dict] = defaultdict(lambda: {"base": Decimal("0"), "tax": Decimal("0")})
    for line in invoice.lines:
        q = Decimal(str(line.quantity))
        up = Decimal(str(line.unit_price))
        disc = Decimal(str(line.discount_percentage or 0)) / 100
        rate_pct = Decimal(str(line.tax_percentage or 21))
        line_base = q * up * (1 - disc)
        line_tax = line_base * rate_pct / 100
        key = _fmt(rate_pct)
        tax_groups[key]["base"] += line_base
        tax_groups[key]["tax"] += line_tax

    if not tax_groups:
        key = "21.00"
        tax_groups[key] = {
            "base": Decimal(str(invoice.amount_base or 0)),
            "tax": Decimal(str(invoice.tax_amount or 0)),
        }

    # ── Root element ──────────────────────────────────────────────────────────
    root = ET.Element(
        "Facturae",
        {
            "xmlns": "http://www.facturae.es/Facturae/2009/v3.2/Facturae",
            "xmlns:ds": "http://www.w3.org/2000/09/xmldsig#",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": (
                "http://www.facturae.es/Facturae/2009/v3.2/Facturae "
                "http://www.facturae.es/Facturae/2009/v3.2/Facturae/Facturaev3_2_2.xsd"
            ),
        },
    )

    # ── FileHeader ────────────────────────────────────────────────────────────
    fh = _sub(root, "FileHeader")
    _sub(fh, "SchemaVersion", "3.2.2")
    _sub(fh, "Modality", "I")
    _sub(fh, "InvoiceIssuerType", "SE")
    batch = _sub(fh, "Batch")
    _sub(batch, "BatchIdentifier", f"{(tenant.nif or '').replace(' ', '')}{inv_num.replace('/', '')}")
    _sub(batch, "InvoicesCount", "1")
    _amount_el(batch, "TotalInvoicesAmount", invoice.amount_total)
    _amount_el(batch, "TotalOutstandingAmount", invoice.amount_total)
    _amount_el(batch, "TotalExecutableAmount", invoice.amount_total)
    _sub(batch, "InvoiceCurrencyCode", "EUR")

    # ── Parties ───────────────────────────────────────────────────────────────
    parties = _sub(root, "Parties")
    _build_party(parties, "SellerParty", tenant.nif or "", tenant.name, tenant.address or "", "", "")
    _build_party(
        parties,
        "BuyerParty",
        client.nif if client else "",
        client.name if client else "",
        client.address if client else "",
        client.postal_code if client else "",
        client.city if client else "",
    )

    # ── Invoices ──────────────────────────────────────────────────────────────
    invoices_el = _sub(root, "Invoices")
    inv_el = _sub(invoices_el, "Invoice")

    inv_header = _sub(inv_el, "InvoiceHeader")
    _sub(inv_header, "InvoiceNumber", inv_num)
    _sub(inv_header, "InvoiceSeriesCode", serie)
    _sub(inv_header, "InvoiceDocumentType", "FC")
    _sub(inv_header, "InvoiceClass", "OO")

    issue_data = _sub(inv_el, "InvoiceIssueData")
    _sub(issue_data, "IssueDate", issue_date)
    _sub(issue_data, "InvoiceCurrencyCode", "EUR")
    _sub(issue_data, "TaxCurrencyCode", "EUR")
    _sub(issue_data, "LanguageName", "es")

    taxes_out = _sub(inv_el, "TaxesOutputs")
    for rate, amounts in tax_groups.items():
        t = _sub(taxes_out, "Tax")
        _sub(t, "TaxTypeCode", "01")
        _sub(t, "TaxRate", rate)
        _amount_el(t, "TaxableBase", amounts["base"])
        _amount_el(t, "TaxAmount", amounts["tax"])

    totals = _sub(inv_el, "InvoiceTotals")
    _sub(totals, "TotalGrossAmount", _fmt(invoice.amount_base))
    _sub(totals, "TotalGeneralDiscounts", "0.00")
    _sub(totals, "TotalGeneralSurcharges", "0.00")
    _sub(totals, "TotalGrossAmountBeforeTaxes", _fmt(invoice.amount_base))
    _sub(totals, "TotalTaxOutputs", _fmt(invoice.tax_amount))
    _sub(totals, "TotalTaxesWithheld", "0.00")
    _sub(totals, "InvoiceTotal", _fmt(invoice.amount_total))
    _sub(totals, "TotalOutstandingAmount", _fmt(invoice.amount_total))
    _sub(totals, "TotalExecutableAmount", _fmt(invoice.amount_total))

    items_el = _sub(inv_el, "Items")
    for line in invoice.lines:
        q = Decimal(str(line.quantity))
        up = Decimal(str(line.unit_price))
        disc = Decimal(str(line.discount_percentage or 0)) / 100
        rate_pct = Decimal(str(line.tax_percentage or 21))
        line_base = q * up * (1 - disc)
        line_tax_amt = line_base * rate_pct / 100

        li = _sub(items_el, "InvoiceLine")
        _sub(li, "ItemDescription", (line.description or "")[:80])
        _sub(li, "Quantity", _fmt(q))
        _sub(li, "UnitOfMeasure", "07")
        _sub(li, "UnitPriceWithoutTax", _fmt(up))
        _sub(li, "TotalCost", _fmt(q * up))
        _sub(li, "DiscountsAndRebates", _fmt(q * up * disc))
        _sub(li, "Charges", "0.00")
        _sub(li, "GrossAmount", _fmt(line_base))
        lt = _sub(li, "TaxesOutputs")
        tax_line = _sub(lt, "Tax")
        _sub(tax_line, "TaxTypeCode", "01")
        _sub(tax_line, "TaxRate", _fmt(rate_pct))
        _amount_el(tax_line, "TaxableBase", line_base)
        _amount_el(tax_line, "TaxAmount", line_tax_amt)

    try:
        ET.indent(root, space="  ")
    except AttributeError:
        pass  # Python < 3.9 fallback

    xml_str = ET.tostring(root, encoding="unicode", xml_declaration=False)
    xml_bytes = b'<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str.encode("utf-8")
    filename = f"facturae_{inv_num.replace('/', '-').replace(' ', '_')}.xsig"
    return xml_bytes, filename
