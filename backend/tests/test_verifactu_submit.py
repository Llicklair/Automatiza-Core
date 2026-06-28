"""Tests de la costura de envío VeriFactu (services/billing/verifactu_submit).

Sin certificado, sin red y sin BD: se mockean la generación del XML, la carga del certificado
y la firma. Cubren el acuse (RespuestaSuministro.xsd), el no-op de no_remission, el gate de
`confirmed` (sin POST por defecto), el camino confirmado (cert→firma→envío→acuse) y sus
abortos seguros (sin cert, firma stub, XML inválido) — nunca se finge un envío.
El handshake mTLS real (`HttpxVerifactuTransport`) NO se ejercita aquí (requiere cert + AEAT).
"""
import uuid
from types import SimpleNamespace

import pytest

from app.services.aeat.certificate_storage import CertificateError
from app.services.aeat.xades_signer import SignResult
from app.services.billing import verifactu_submit as vs

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
    def __init__(self, response: str = _ACUSE_CORRECTO, *, fail_if_called: bool = False):
        self.response = response
        self.calls = 0
        self._fail_if_called = fail_if_called

    async def send(self, *, signed_xml: str, pfx: bytes, password: str, environment: str) -> str:
        self.calls += 1
        if self._fail_if_called:
            raise AssertionError("transport.send NO debía llamarse")
        return self.response


def _patch(monkeypatch, *, xml_valid=True, cert_error=False, signed=True, sif_nif="B11111111"):
    """Mockea generación de XML, carga de cert y firma (evita BD/cert/red).

    `sif_nif`: NIF del SIF (productor) que ve el guard de cumplimiento de
    `submit()`. Por defecto un NIF real para ejercitar el camino de envío; pasar
    `sif_nif=None` deja el placeholder "B00000000" (default) para probar que el
    guard B2 bloquea el envío.
    """
    async def _gen(db, *, record, sistema=None):
        return "<RegFactuSistemaFacturacion/>"

    async def _load(db, tenant_id):
        if cert_error:
            raise CertificateError("No hay certificado activo para este tenant.")
        return (b"PFXBYTES", "pwd")

    def _sign(xml, pfx, password):
        return SignResult(
            signed_xml="<RegFactuSistemaFacturacion firmado='1'/>" if signed else "<UnsignedDraft/>",
            signed=signed,
            method="xades-bes" if signed else "stub",
            warnings=[] if signed else ["stub: falta libxmlsec1"],
        )

    monkeypatch.setattr("app.services.billing.registro_facturacion.generate_alta_xml", _gen)
    monkeypatch.setattr(
        "app.services.billing.registro_facturacion.validate_verifactu_xml",
        lambda xml: [] if xml_valid else ["error XSD simulado"],
    )
    monkeypatch.setattr("app.services.aeat.certificate_storage.load_decrypted", _load)
    monkeypatch.setattr("app.services.aeat.xades_signer.sign_xades_bes", _sign)
    if sif_nif is not None:
        from app.services.billing.registro_facturacion import SistemaInformatico

        sistema = SistemaInformatico(
            nombre_razon="Productor Test S.L.",
            nif=sif_nif,
            nombre_sistema="AutomatizaCore",
            id_sistema="01",
            version="1.0",
            numero_instalacion="0001",
        )
        monkeypatch.setattr(
            "app.services.billing.registro_facturacion.default_sistema_informatico",
            lambda: sistema,
        )


_REC = SimpleNamespace(tenant_id=uuid.uuid4())


@pytest.mark.asyncio
class TestSubmitters:
    async def test_no_remission_es_noop(self):
        ack = await vs.NoRemissionSubmitter().submit(None, record=_REC)
        assert ack.remitted is False and ack.dry_run is False
        assert "no_remission" in ack.detail

    async def test_dry_run_no_carga_cert_ni_envia(self, monkeypatch):
        _patch(monkeypatch, xml_valid=True)
        transport = _FakeTransport(fail_if_called=True)
        ack = await vs.PreproduccionSubmitter(transport=transport).submit(
            None, record=_REC, confirmed=False
        )
        assert ack.dry_run is True and ack.remitted is False
        assert transport.calls == 0  # garantía: sin confirmed NO hay POST

    async def test_confirmed_firma_y_envia(self, monkeypatch):
        _patch(monkeypatch, signed=True)
        transport = _FakeTransport(_ACUSE_CORRECTO)
        ack = await vs.PreproduccionSubmitter(transport=transport).submit(
            None, record=_REC, confirmed=True
        )
        assert transport.calls == 1
        assert ack.remitted is True and ack.estado_envio == "Correcto"
        assert ack.csv == "ABCDEF1234567890"

    async def test_confirmed_sin_certificado_aborta(self, monkeypatch):
        _patch(monkeypatch, cert_error=True)
        transport = _FakeTransport(fail_if_called=True)
        with pytest.raises(CertificateError):
            await vs.PreproduccionSubmitter(transport=transport).submit(
                None, record=_REC, confirmed=True
            )
        assert transport.calls == 0

    async def test_confirmed_sif_nif_placeholder_aborta(self, monkeypatch):
        """B2: con el NIF del SIF (productor) en placeholder 'B00000000' NO se
        remite a la AEAT aunque confirmed=True. Se aborta ANTES de cargar el
        certificado o firmar — nunca se envía un registro con NIF de productor
        ficticio (RD 1007/2023 + Orden HAC/1177/2024)."""
        _patch(monkeypatch, sif_nif=None)  # deja el placeholder por defecto
        transport = _FakeTransport(fail_if_called=True)
        with pytest.raises(vs.VerifactuSubmitError, match="VERIFACTU_SIF_NIF"):
            await vs.PreproduccionSubmitter(transport=transport).submit(
                None, record=_REC, confirmed=True
            )
        assert transport.calls == 0

    async def test_confirmed_firma_stub_no_envia(self, monkeypatch):
        _patch(monkeypatch, signed=False)
        transport = _FakeTransport(fail_if_called=True)
        with pytest.raises(vs.VerifactuSubmitError):
            await vs.PreproduccionSubmitter(transport=transport).submit(
                None, record=_REC, confirmed=True
            )
        assert transport.calls == 0  # firma stub → NO se envía, no se finge

    async def test_xml_invalido_aborta(self, monkeypatch):
        _patch(monkeypatch, xml_valid=False)
        transport = _FakeTransport(fail_if_called=True)
        with pytest.raises(vs.VerifactuSubmitError):
            await vs.PreproduccionSubmitter(transport=transport).submit(
                None, record=_REC, confirmed=True
            )
        assert transport.calls == 0


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
