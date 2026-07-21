"""Contenido del registro de alta (P2/P5 del audit 2026-07-21).

- Bloque `Destinatarios` obligatorio en F1/F3/R1 (fail-closed sin NIF).
- F2 sin destinatario (art. 61.d); R5 sin NIF lleva el indicador.
- Calificación REAL: S1 solo con tipo > 0; 0% exige `exencion_causa`
  (E1–E6 → OperacionExenta; N1/N2 → no sujeta; sin causa → bloqueo).
"""

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


def _record(tipo="F1", num="FA2026/001"):
    payload = build_payload_alta(
        id_emisor=_NIF,
        num_serie_factura=num,
        fecha_expedicion=_fmt_fecha_expedicion(_FECHA),
        tipo_factura=tipo,
        cuota_total=Decimal("21.00"),
        importe_total=Decimal("121.00"),
        huella_anterior=None,
        fecha_hora_gen=_FHG,
    )
    return SimpleNamespace(
        payload_canonico=payload,
        huella=compute_huella(payload),
        huella_anterior=None,
        nif_emisor=_NIF,
        numero_factura=num,
        fecha_emision=_FECHA,
    )


def _inv(exencion=None):
    return SimpleNamespace(amount_base=Decimal("100.00"), tax_amount=Decimal("21.00"), exencion_causa=exencion)


def _line(rate="21.00"):
    return [
        SimpleNamespace(
            quantity=Decimal("1"),
            unit_price=Decimal("100.00"),
            tax_percentage=Decimal(rate),
            description="Servicio",
        )
    ]


def _assert_xsd_ok(xml: str) -> None:
    if _XSD_PRESENT and _LXML:
        assert rf.validate_verifactu_xml(xml) == []


class TestDestinatarios:
    def test_f1_incluye_destinatarios(self):
        xml = rf.build_registro_alta_xml(
            record=_record(),
            invoice=_inv(),
            emisor_nombre="EMPRESA SL",
            lines=_line(),
            destinatario_nombre="CLIENTE SL",
            destinatario_nif="A11111111",
        )
        assert "Destinatarios" in xml
        assert "A11111111" in xml
        assert "CLIENTE SL" in xml
        _assert_xsd_ok(xml)

    def test_f1_sin_nif_bloquea(self):
        with pytest.raises(ValueError, match="destinatario"):
            rf.build_registro_alta_xml(record=_record(), invoice=_inv(), emisor_nombre="E", lines=_line())

    def test_f2_sin_destinatarios_con_indicador(self):
        xml = rf.build_registro_alta_xml(record=_record(tipo="F2"), invoice=_inv(), emisor_nombre="E", lines=_line())
        assert "Destinatarios" not in xml
        assert "FacturaSinIdentifDestinatarioArt61d" in xml
        _assert_xsd_ok(xml)

    def test_r5_sin_nif_lleva_indicador(self):
        xml = rf.build_registro_alta_xml(
            record=_record(tipo="R5"),
            invoice=_inv(),
            emisor_nombre="E",
            lines=_line(),
            rectified_invoice=SimpleNamespace(invoice_number="T-1", date=_FECHA),
        )
        assert "FacturaSinIdentifDestinatarioArt61d" in xml
        assert "Destinatarios" not in xml
        _assert_xsd_ok(xml)


class TestCalificacion:
    def _xml(self, exencion, rate="0"):
        return rf.build_registro_alta_xml(
            record=_record(),
            invoice=_inv(exencion=exencion),
            emisor_nombre="E",
            lines=_line(rate),
            destinatario_nombre="C",
            destinatario_nif="A11111111",
        )

    def test_exenta_e1_emite_operacion_exenta(self):
        xml = self._xml("E1")
        assert "OperacionExenta" in xml
        assert ">E1<" in xml
        assert "TipoImpositivo" not in xml
        assert "CuotaRepercutida" not in xml
        _assert_xsd_ok(xml)

    def test_no_sujeta_n1(self):
        xml = self._xml("N1")
        assert "OperacionExenta" not in xml
        assert ">N1<" in xml
        _assert_xsd_ok(xml)

    def test_cero_sin_causa_bloquea(self):
        with pytest.raises(ValueError, match="exenci"):
            self._xml(None)

    def test_tipo_positivo_sigue_s1(self):
        xml = self._xml(None, rate="21.00")
        assert ">S1<" in xml
        assert "TipoImpositivo" in xml
        _assert_xsd_ok(xml)
