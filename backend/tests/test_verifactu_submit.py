"""Tests de la costura de envío VeriFactu (services/billing/verifactu_submit).

Sin certificado, sin red y sin BD: se mockean la generación del XML y el modo del tenant.
Cubren: parseo del acuse (RespuestaSuministro.xsd) en sus variantes, el no-op de no_remission,
el gate de `confirmed` (no hay POST por defecto), el camino "sin transporte real" (NotImplemented)
y la factory por modo. El envío real (cert-gated) NO se ejercita aquí a propósito.
"""
import uuid

import pytest

from app.services.billing import verifactu_submit as vs

# ── Acuses de ejemplo (parseados por local-name → tolerantes a prefijos/SOAP) ──

_NS = 'xmlns="https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/RespuestaSuministro.xsd"'

_ACUSE_CORRECTO = f"""<RespuestaRegFactuSistemaFacturacion {_NS}>
  <CSV>ABCDEF1234567890</CSV>
  <TiempoEsperaEnvio>60</TiempoEsperaEnvio>
  <EstadoEnvio>Correcto</EstadoEnvio>
  <RespuestaLinea>
    <IDFactura>
      <IDEmisorFactura>B12345678</IDEmisorFactura>
      <NumSerieFactura>FA2026/001</NumSerieFactura>
      <FechaExpedicionFactura>14-06-2026</FechaExpedicionFactura>
    </IDFactura>
    <EstadoRegistro>Correcto</EstadoRegistro>
  </RespuestaLinea>
</RespuestaRegFactuSistemaFacturacion>"""

_ACUSE_INCORRECTO = f"""<RespuestaRegFactuSistemaFacturacion {_NS}>
  <EstadoEnvio>Incorrecto</EstadoEnvio>
  <RespuestaLinea>
    <IDFactura>
      <IDEmisorFactura>B12345678</IDEmisorFactura>
      <NumSerieFactura>FA2026/002</NumSerieFactura>
      <FechaExpedicionFactura>14-06-2026</FechaExpedicionFactura>
    </IDFactura>
    <EstadoRegistro>Incorrecto</EstadoRegistro>
    <CodigoErrorRegistro>3001</CodigoErrorRegistro>
    <DescripcionErrorRegistro>NIF del emisor no identificado</DescripcionErrorRegistro>
  </RespuestaLinea>
</RespuestaRegFactuSistemaFacturacion>"""

_ACUSE_DUPLICADO = f"""<RespuestaRegFactuSistemaFacturacion {_NS}>
  <CSV>CSVPARCIAL999</CSV>
  <EstadoEnvio>ParcialmenteCorrecto</EstadoEnvio>
  <RespuestaLinea>
    <IDFactura>
      <IDEmisorFactura>B12345678</IDEmisorFactura>
      <NumSerieFactura>FA2026/003</NumSerieFactura>
      <FechaExpedicionFactura>14-06-2026</FechaExpedicionFactura>
    </IDFactura>
    <EstadoRegistro>AceptadoConErrores</EstadoRegistro>
    <CodigoErrorRegistro>3500</CodigoErrorRegistro>
    <DescripcionErrorRegistro>Registro duplicado</DescripcionErrorRegistro>
    <RegistroDuplicado>
      <EstadoRegistroDuplicado>Correcta</EstadoRegistroDuplicado>
    </RegistroDuplicado>
  </RespuestaLinea>
</RespuestaRegFactuSistemaFacturacion>"""

# Mismo acuse Correcto pero envuelto en SOAP y con prefijos explícitos distintos.
_ACUSE_SOAP = """<env:Envelope xmlns:env="http://schemas.xmlsoap.org/soap/envelope/">
  <env:Body>
    <sfR:RespuestaRegFactuSistemaFacturacion
        xmlns:sfR="https://www2.agenciatributaria.gob.es/x/RespuestaSuministro.xsd"
        xmlns:sf="https://www2.agenciatributaria.gob.es/x/SuministroInformacion.xsd">
      <sfR:CSV>CSVSOAP777</sfR:CSV>
      <sfR:EstadoEnvio>Correcto</sfR:EstadoEnvio>
      <sfR:RespuestaLinea>
        <sf:IDFactura>
          <sf:IDEmisorFactura>B12345678</sf:IDEmisorFactura>
          <sf:NumSerieFactura>FA2026/009</sf:NumSerieFactura>
          <sf:FechaExpedicionFactura>14-06-2026</sf:FechaExpedicionFactura>
        </sf:IDFactura>
        <sfR:EstadoRegistro>Correcto</sfR:EstadoRegistro>
      </sfR:RespuestaLinea>
    </sfR:RespuestaRegFactuSistemaFacturacion>
  </env:Body>
</env:Envelope>"""


class TestParseAcuse:
    def test_correcto(self):
        ack = vs.parse_acuse(_ACUSE_CORRECTO)
        assert ack.remitted is True and ack.dry_run is False
        assert ack.estado_envio == "Correcto"
        assert ack.csv == "ABCDEF1234567890"
        assert ack.tiempo_espera_envio == 60
        assert len(ack.lineas) == 1
        l = ack.lineas[0]
        assert l.id_emisor == "B12345678" and l.num_serie == "FA2026/001"
        assert l.estado_registro == "Correcto"
        assert l.codigo_error is None and l.duplicado is False

    def test_incorrecto(self):
        ack = vs.parse_acuse(_ACUSE_INCORRECTO)
        assert ack.estado_envio == "Incorrecto"
        assert ack.csv is None  # no hay CSV si el envío se rechaza
        l = ack.lineas[0]
        assert l.estado_registro == "Incorrecto"
        assert l.codigo_error == 3001
        assert l.descripcion_error == "NIF del emisor no identificado"

    def test_parcialmente_correcto_y_duplicado(self):
        ack = vs.parse_acuse(_ACUSE_DUPLICADO)
        assert ack.estado_envio == "ParcialmenteCorrecto"
        assert ack.csv == "CSVPARCIAL999"
        l = ack.lineas[0]
        assert l.estado_registro == "AceptadoConErrores"
        assert l.codigo_error == 3500
        assert l.duplicado is True

    def test_soap_envuelto_y_prefijos(self):
        ack = vs.parse_acuse(_ACUSE_SOAP)
        assert ack.estado_envio == "Correcto"
        assert ack.csv == "CSVSOAP777"
        assert ack.lineas[0].num_serie == "FA2026/009"

    def test_respuesta_irreconocible_lanza(self):
        with pytest.raises(vs.VerifactuSubmitError):
            vs.parse_acuse("<env:Fault xmlns:env='x'><faultcode>soap</faultcode></env:Fault>")

    def test_xml_invalido_lanza(self):
        with pytest.raises(vs.VerifactuSubmitError):
            vs.parse_acuse("esto no es xml")


class _FakeTransport:
    """Transporte de test: cuenta llamadas y devuelve un acuse fijo."""

    def __init__(self, response: str = _ACUSE_CORRECTO, *, fail_if_called: bool = False):
        self.response = response
        self.calls = 0
        self._fail_if_called = fail_if_called

    async def post(self, *, xml: str, environment: str, confirmed: bool) -> str:
        self.calls += 1
        if self._fail_if_called:
            raise AssertionError("transport.post NO debía llamarse")
        return self.response


def _patch_xml(monkeypatch, *, valid: bool = True):
    """Mockea generate_alta_xml/validate_verifactu_xml (evita BD/cert)."""
    async def _gen(db, *, record, sistema=None):
        return "<RegFactuSistemaFacturacion/>"

    monkeypatch.setattr(
        "app.services.billing.registro_facturacion.generate_alta_xml", _gen
    )
    monkeypatch.setattr(
        "app.services.billing.registro_facturacion.validate_verifactu_xml",
        lambda xml: [] if valid else ["error XSD simulado"],
    )


@pytest.mark.asyncio
class TestSubmitters:
    async def test_no_remission_es_noop(self):
        ack = await vs.NoRemissionSubmitter().submit(None, record=object())
        assert ack.remitted is False and ack.dry_run is False
        assert "no_remission" in ack.detail

    async def test_dry_run_no_llama_al_transporte(self, monkeypatch):
        _patch_xml(monkeypatch, valid=True)
        transport = _FakeTransport(fail_if_called=True)
        sub = vs.PreproduccionSubmitter(transport=transport)
        ack = await sub.submit(None, record=object(), confirmed=False)
        assert ack.dry_run is True and ack.remitted is False
        assert transport.calls == 0  # garantía: sin confirmed NO hay POST

    async def test_confirmed_envia_y_parsea_acuse(self, monkeypatch):
        _patch_xml(monkeypatch, valid=True)
        transport = _FakeTransport(_ACUSE_CORRECTO)
        sub = vs.PreproduccionSubmitter(transport=transport)
        ack = await sub.submit(None, record=object(), confirmed=True)
        assert transport.calls == 1
        assert ack.remitted is True and ack.estado_envio == "Correcto"
        assert ack.csv == "ABCDEF1234567890"

    async def test_confirmed_sin_transporte_no_finge(self, monkeypatch):
        _patch_xml(monkeypatch, valid=True)
        sub = vs.PreproduccionSubmitter(transport=None)
        with pytest.raises(NotImplementedError):
            await sub.submit(None, record=object(), confirmed=True)

    async def test_xml_invalido_aborta(self, monkeypatch):
        _patch_xml(monkeypatch, valid=False)
        transport = _FakeTransport(fail_if_called=True)
        sub = vs.PreproduccionSubmitter(transport=transport)
        with pytest.raises(vs.VerifactuSubmitError):
            await sub.submit(None, record=object(), confirmed=True)
        assert transport.calls == 0  # no se envía un XML que no valida


@pytest.mark.asyncio
class TestFactory:
    async def test_no_remission_devuelve_noop(self, monkeypatch):
        async def _mode(db, *, tenant_id):
            return "no_remission"
        monkeypatch.setattr("app.services.billing.verifactu_mode.get_mode", _mode)
        sub = await vs.get_submitter(None, tenant_id=uuid.uuid4())
        assert isinstance(sub, vs.NoRemissionSubmitter)

    async def test_voluntary_devuelve_preproduccion(self, monkeypatch):
        async def _mode(db, *, tenant_id):
            return "voluntary"
        monkeypatch.setattr("app.services.billing.verifactu_mode.get_mode", _mode)
        sub = await vs.get_submitter(None, tenant_id=uuid.uuid4())
        assert isinstance(sub, vs.PreproduccionSubmitter)
