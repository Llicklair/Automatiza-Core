"""VeriFactu — el XML RegistroAlta/Anulación valida contra el XSD oficial AEAT.

Tests puros (sin DB) del builder `services/billing/registro_facturacion`. La
validación XSD se omite (skip) si faltan los esquemas oficiales en
`services/aeat/xsd/` o si `lxml` no está instalado; el resto de aserciones
estructurales corren siempre.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.billing import registro_facturacion as rf
from app.services.billing.verifactu_chain import (
    _fmt_fecha_expedicion,
    _fmt_fecha_hora_gen,
    build_payload_alta,
    compute_huella,
)

_XSD_PRESENT = (Path(rf.__file__).parents[1] / "aeat" / "xsd" / "SuministroLR.xsd").exists()
try:
    import lxml  # noqa: F401

    _LXML = True
except ImportError:
    _LXML = False

_NIF = "B12345678"
_FECHA = datetime(2026, 6, 14, tzinfo=UTC)
_FHG = _fmt_fecha_hora_gen(datetime(2026, 6, 14, 10, 30, 0, tzinfo=UTC).astimezone())


def _make_record(num="FA2026/001", *, huella_anterior=None, cuota="21.00", importe="121.00"):
    payload = build_payload_alta(
        id_emisor=_NIF,
        num_serie_factura=num,
        fecha_expedicion=_fmt_fecha_expedicion(_FECHA),
        tipo_factura="F1",
        cuota_total=Decimal(cuota),
        importe_total=Decimal(importe),
        huella_anterior=huella_anterior,
        fecha_hora_gen=_FHG,
    )
    return SimpleNamespace(
        payload_canonico=payload,
        huella=compute_huella(payload),
        huella_anterior=huella_anterior,
        nif_emisor=_NIF,
        numero_factura=num,
        fecha_emision=_FECHA,
    )


def _invoice():
    return SimpleNamespace(amount_base=Decimal("100.00"), tax_amount=Decimal("21.00"))


def _lines():
    return [
        SimpleNamespace(
            quantity=Decimal("1"),
            unit_price=Decimal("100.00"),
            tax_percentage=Decimal("21.00"),
            description="Consultoría",
        )
    ]


_xsd_required = pytest.mark.skipif(
    not (_XSD_PRESENT and _LXML),
    reason="XSD oficiales AEAT o lxml no disponibles (ejecutar scripts/update_aeat_xsd.py)",
)


@_xsd_required
def test_alta_primer_registro_valida_xsd():
    record = _make_record()
    xml = rf.build_registro_alta_xml(
        record=record, invoice=_invoice(), emisor_nombre="EMPRESA EJEMPLO SL", lines=_lines()
    )
    assert rf.validate_verifactu_xml(xml) == []
    assert "PrimerRegistro" in xml
    assert record.huella in xml


@_xsd_required
def test_f2_incluye_sin_identif_destinatario_valida_xsd():
    payload = build_payload_alta(
        id_emisor=_NIF,
        num_serie_factura="T2026/001",
        fecha_expedicion=_fmt_fecha_expedicion(_FECHA),
        tipo_factura="F2",
        cuota_total=Decimal("21.00"),
        importe_total=Decimal("121.00"),
        huella_anterior=None,
        fecha_hora_gen=_FHG,
    )
    record = SimpleNamespace(
        payload_canonico=payload,
        huella=compute_huella(payload),
        huella_anterior=None,
        nif_emisor=_NIF,
        numero_factura="T2026/001",
        fecha_emision=_FECHA,
    )
    xml = rf.build_registro_alta_xml(record=record, invoice=_invoice(), emisor_nombre="TINTORERIA SL", lines=_lines())
    assert rf.validate_verifactu_xml(xml) == []
    assert "FacturaSinIdentifDestinatarioArt61d" in xml


def test_f1_no_incluye_sin_identif_destinatario():
    record = _make_record()  # F1
    xml = rf.build_registro_alta_xml(record=record, invoice=_invoice(), emisor_nombre="EMPRESA SL", lines=_lines())
    assert "FacturaSinIdentifDestinatarioArt61d" not in xml


@_xsd_required
def test_f3_sustitutiva_incluye_facturas_sustituidas_valida_xsd():
    payload = build_payload_alta(
        id_emisor=_NIF,
        num_serie_factura="FA2026/010",
        fecha_expedicion=_fmt_fecha_expedicion(_FECHA),
        tipo_factura="F3",
        cuota_total=Decimal("21.00"),
        importe_total=Decimal("121.00"),
        huella_anterior=None,
        fecha_hora_gen=_FHG,
    )
    record = SimpleNamespace(
        payload_canonico=payload,
        huella=compute_huella(payload),
        huella_anterior=None,
        nif_emisor=_NIF,
        numero_factura="FA2026/010",
        fecha_emision=_FECHA,
    )
    substituida = SimpleNamespace(invoice_number="T2026/001", date=_FECHA)
    xml = rf.build_registro_alta_xml(
        record=record,
        invoice=_invoice(),
        emisor_nombre="TINTORERIA SL",
        lines=_lines(),
        substituted_invoice=substituida,
    )
    assert rf.validate_verifactu_xml(xml) == []
    assert "FacturasSustituidas" in xml
    assert "IDFacturaSustituida" in xml
    assert "T2026/001" in xml  # NumSerie de la simplificada sustituida


@_xsd_required
def test_alta_encadenado_valida_xsd():
    prev = _make_record("FA2026/001")
    record = _make_record("FA2026/002", huella_anterior=prev.huella, cuota="10.50", importe="60.50")
    xml = rf.build_registro_alta_xml(
        record=record,
        invoice=_invoice(),
        emisor_nombre="EMPRESA EJEMPLO SL",
        lines=_lines(),
        prev_record=prev,
    )
    assert rf.validate_verifactu_xml(xml) == []
    assert "RegistroAnterior" in xml
    assert prev.huella in xml  # la huella anterior va en el RegistroAnterior


@_xsd_required
def test_anulacion_valida_xsd():
    prev = _make_record("FA2026/002")
    xml = rf.build_registro_anulacion_xml(
        emisor_nombre="EMPRESA EJEMPLO SL",
        emisor_nif=_NIF,
        num_serie="FA2026/001",
        fecha_expedicion="14-06-2026",
        huella="A" * 64,
        fecha_hora_gen=_FHG,
        huella_anterior=prev.huella,
        prev_record=prev,
    )
    assert rf.validate_verifactu_xml(xml) == []
    assert "RegistroAnulacion" in xml
    assert "NumSerieFacturaAnulada" in xml


@_xsd_required
def test_rectificativa_incluye_tipo_y_facturas_rectificadas_valida_xsd():
    """B3: una rectificativa (R1) emite `TipoRectificativa` + `FacturasRectificadas`
    referenciando la original, y valida contra el XSD oficial. Como
    `create_rectificativa` genera líneas NEGADAS (reversión total), el tipo es
    'I' (por diferencias/incremental)."""
    payload = build_payload_alta(
        id_emisor=_NIF,
        num_serie_factura="R2026/001",
        fecha_expedicion=_fmt_fecha_expedicion(_FECHA),
        tipo_factura="R1",
        cuota_total=Decimal("-21.00"),
        importe_total=Decimal("-121.00"),
        huella_anterior=None,
        fecha_hora_gen=_FHG,
    )
    record = SimpleNamespace(
        payload_canonico=payload,
        huella=compute_huella(payload),
        huella_anterior=None,
        nif_emisor=_NIF,
        numero_factura="R2026/001",
        fecha_emision=_FECHA,
    )
    rect_invoice = SimpleNamespace(amount_base=Decimal("-100.00"), tax_amount=Decimal("-21.00"))
    neg_lines = [
        SimpleNamespace(
            quantity=Decimal("1"),
            unit_price=Decimal("-100.00"),
            tax_percentage=Decimal("21.00"),
            description="Abono Consultoría",
        )
    ]
    original = SimpleNamespace(invoice_number="FA2026/001", date=_FECHA)

    xml = rf.build_registro_alta_xml(
        record=record,
        invoice=rect_invoice,
        emisor_nombre="EMPRESA EJEMPLO SL",
        lines=neg_lines,
        rectified_invoice=original,
    )
    assert rf.validate_verifactu_xml(xml) == []
    assert "TipoRectificativa>I<" in xml
    assert "FacturasRectificadas" in xml
    assert "IDFacturaRectificada" in xml
    assert "FA2026/001" in xml  # NumSerie de la factura original rectificada


@_xsd_required
def test_alta_normal_no_incluye_campos_rectificativa():
    """Control (no sobre-emisión): una F1 sin original NO lleva TipoRectificativa."""
    record = _make_record()
    xml = rf.build_registro_alta_xml(record=record, invoice=_invoice(), emisor_nombre="EMPRESA SL", lines=_lines())
    assert rf.validate_verifactu_xml(xml) == []
    assert "TipoRectificativa" not in xml
    assert "FacturasRectificadas" not in xml


@_xsd_required
def test_multiples_tipos_iva_generan_varios_detalles():
    record = _make_record(cuota="31.50", importe="231.50")
    lines = [
        SimpleNamespace(
            quantity=Decimal("1"), unit_price=Decimal("100.00"), tax_percentage=Decimal("21.00"), description="A"
        ),
        SimpleNamespace(
            quantity=Decimal("1"), unit_price=Decimal("100.00"), tax_percentage=Decimal("10.50"), description="B"
        ),
    ]
    xml = rf.build_registro_alta_xml(record=record, invoice=_invoice(), emisor_nombre="EMPRESA SL", lines=lines)
    assert rf.validate_verifactu_xml(xml) == []
    assert xml.count("DetalleDesglose") == 2 * 2  # apertura + cierre por detalle


def test_huella_xml_coincide_con_payload():
    """La Huella del XML DEBE ser SHA-256 del payload canónico almacenado."""
    record = _make_record()
    xml = rf.build_registro_alta_xml(record=record, invoice=_invoice(), emisor_nombre="EMPRESA SL", lines=_lines())
    assert compute_huella(record.payload_canonico) in xml


def test_registro_anterior_sin_prev_record_falla():
    """Con huella_anterior pero sin prev_record no se puede identificar la previa."""
    record = _make_record("FA2026/002", huella_anterior="DEAD" * 16)
    with pytest.raises(ValueError, match="prev_record"):
        rf.build_registro_alta_xml(record=record, invoice=_invoice(), emisor_nombre="EMPRESA SL", lines=_lines())


def test_parse_payload_roundtrip():
    d = rf._parse_payload("IDEmisorFactura=B1&NumSerieFactura=A/1&Huella=&TipoFactura=F1")
    assert d["IDEmisorFactura"] == "B1"
    assert d["NumSerieFactura"] == "A/1"
    assert d["Huella"] == ""
    assert d["TipoFactura"] == "F1"


def test_id_sistema_informatico_max_2_chars():
    s = rf.default_sistema_informatico()
    assert len(s.id_sistema) <= 2
