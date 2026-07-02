"""Envío VeriFactu a la AEAT (modelo BYO: el certificado lo pone la pyme).

Reutiliza la maquinaria de presentación ya existente — `certificate_storage` (cert del
tenant), `xades_signer.sign_xades_bes` (firma XAdES) — igual que la presentación de modelos
303/130. El flujo, **gated**:

  no_remission (default) → no-op (idéntico a hoy).
  voluntary + confirmed  → cargar cert del tenant → validar XML contra XSD → firmar XAdES →
                           POST SOAP (mTLS con el cert) → parsear el acuse oficial.

Cautela (línea roja): sin `confirmed=True` **no hay POST** (dry-run, sin CSV). Sin certificado
activo o con firma *stub* (sin libxmlsec1) se **aborta sin enviar** — nunca se finge un envío ni
un CSV/justificante. El `CSV` solo procede del acuse real parseado (`parse_acuse`).

POR CONFIRMAR contra AEAT (no verificable sin certificado + preproducción): el endpoint exacto,
el sobre SOAP y el perfil XAdES de VeriFactu. Ver `tasks/verifactu_envio_spec.md`.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.aeat import certificate_storage as _certs
from app.services.aeat import xades_signer as _signer
from app.services.billing import registro_facturacion as _rf
from app.services.billing import verifactu_mode as _mode

# Endpoints del web service VeriFactu (Suministro de Registros de Facturación).
# POR CONFIRMAR contra el WSDL oficial con un certificado de preproducción.
VERIFACTU_ENDPOINTS: dict[str, str | None] = {
    "preproduccion": "https://prewww1.aeat.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP",
    "produccion": None,  # tras homologar en preproducción
}


class VerifactuSubmitError(Exception):
    """Error de la costura de envío (XML inválido, sin cert, firma stub, acuse irreconocible)."""


# ── Acuse (RespuestaRegFactuSistemaFacturacion, RespuestaSuministro.xsd) ──────


@dataclass(frozen=True)
class VerifactuLineAck:
    id_emisor: str | None
    num_serie: str | None
    fecha_expedicion: str | None
    estado_registro: str | None  # Correcto | AceptadoConErrores | Incorrecto
    codigo_error: int | None
    descripcion_error: str | None
    duplicado: bool


@dataclass(frozen=True)
class VerifactuAck:
    """Acuse del envío. `csv` SOLO se rellena desde una respuesta real de la AEAT."""

    remitted: bool
    estado_envio: str | None = None  # Correcto | ParcialmenteCorrecto | Incorrecto
    csv: str | None = None
    tiempo_espera_envio: int | None = None
    lineas: tuple[VerifactuLineAck, ...] = ()
    raw_response: str | None = None
    dry_run: bool = False
    detail: str = ""


def _ln(tag: str) -> str:
    """Local-name de un tag (ignora namespace) → robusto a prefijos y al sobre SOAP."""
    return tag.rsplit("}", 1)[-1]


def _direct_text(parent: ET.Element, name: str) -> str | None:
    for child in parent:
        if _ln(child.tag) == name:
            return (child.text or "").strip() or None
    return None


def parse_acuse(response_xml: str) -> VerifactuAck:
    """Parsea el cuerpo `RespuestaRegFactuSistemaFacturacion` (puede venir envuelto en SOAP).

    Puro: sin red ni BD. Localiza por local-name → tolera prefijos y el sobre SOAP.
    """
    try:
        root = ET.fromstring(response_xml)
    except ET.ParseError as e:
        raise VerifactuSubmitError(f"Respuesta VeriFactu no es XML válido: {e}") from e

    resp = (
        root
        if _ln(root.tag) == "RespuestaRegFactuSistemaFacturacion"
        else next(
            (e for e in root.iter() if _ln(e.tag) == "RespuestaRegFactuSistemaFacturacion"),
            None,
        )
    )
    if resp is None:
        raise VerifactuSubmitError("Respuesta sin RespuestaRegFactuSistemaFacturacion (¿fault SOAP?)")

    tiempo = _direct_text(resp, "TiempoEsperaEnvio")
    lineas: list[VerifactuLineAck] = []
    for linea in resp:
        if _ln(linea.tag) != "RespuestaLinea":
            continue
        idf = next((c for c in linea if _ln(c.tag) == "IDFactura"), None)

        def _idf(name: str, _idf=idf) -> str | None:
            if _idf is None:
                return None
            for c in _idf.iter():
                if _ln(c.tag) == name:
                    return (c.text or "").strip() or None
            return None

        cod = _direct_text(linea, "CodigoErrorRegistro")
        lineas.append(
            VerifactuLineAck(
                id_emisor=_idf("IDEmisorFactura"),
                num_serie=_idf("NumSerieFactura"),
                fecha_expedicion=_idf("FechaExpedicionFactura"),
                estado_registro=_direct_text(linea, "EstadoRegistro"),
                codigo_error=int(cod) if cod and cod.lstrip("-").isdigit() else None,
                descripcion_error=_direct_text(linea, "DescripcionErrorRegistro"),
                duplicado=any(_ln(c.tag) == "RegistroDuplicado" for c in linea),
            )
        )

    return VerifactuAck(
        remitted=True,
        estado_envio=_direct_text(resp, "EstadoEnvio"),
        csv=_direct_text(resp, "CSV"),
        tiempo_espera_envio=int(tiempo) if tiempo and tiempo.lstrip("-").isdigit() else None,
        lineas=tuple(lineas),
        raw_response=response_xml,
        dry_run=False,
        detail="acuse AEAT parseado",
    )


# ── Transporte (POST mTLS al WS VeriFactu) ────────────────────────────────────


class VerifactuTransport(Protocol):
    """Envía el XML ya firmado y devuelve el cuerpo XML crudo del acuse."""

    async def send(self, *, signed_xml: str, pfx: bytes, password: str, environment: str) -> str: ...


def _client_ssl_context(pfx_bytes: bytes, password: str):
    """SSLContext con el certificado del tenant para mTLS.

    `ssl` no carga cert+clave desde memoria → se materializa un PEM temporal 0600 que se
    borra inmediatamente tras cargarlo. La clave privada solo existe en disco ese instante.
    """
    import os
    import ssl
    import tempfile

    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
        pkcs12,
    )

    key, cert, chain = pkcs12.load_key_and_certificates(pfx_bytes, password.encode("utf-8") if password else None)
    if key is None or cert is None:
        raise VerifactuSubmitError("El certificado no contiene clave privada o cert para mTLS.")

    pem = cert.public_bytes(Encoding.PEM)
    pem += key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
    for extra in chain or []:
        pem += extra.public_bytes(Encoding.PEM)

    ctx = ssl.create_default_context()
    fd, path = tempfile.mkstemp(suffix=".pem")
    try:
        os.write(fd, pem)
        os.close(fd)
        ctx.load_cert_chain(path)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    return ctx


class HttpxVerifactuTransport:
    """POST SOAP con mTLS al WS VeriFactu. Endpoint/sobre/perfil XAdES POR CONFIRMAR (sección
    5 de `tasks/verifactu_envio_spec.md`) — no verificable sin certificado + preproducción."""

    async def send(self, *, signed_xml: str, pfx: bytes, password: str, environment: str) -> str:
        endpoint = VERIFACTU_ENDPOINTS.get(environment)
        if not endpoint:
            raise VerifactuSubmitError(f"Endpoint VeriFactu de '{environment}' no configurado (POR CONFIRMAR).")
        import httpx

        ctx = _client_ssl_context(pfx, password)
        headers = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": ""}
        try:
            async with httpx.AsyncClient(verify=ctx, timeout=60) as client:
                r = await client.post(endpoint, content=signed_xml.encode("utf-8"), headers=headers)
        except httpx.HTTPError as e:
            raise VerifactuSubmitError(f"Error HTTP al enviar a la SEDE VeriFactu: {e}") from e
        if r.status_code >= 400:
            raise VerifactuSubmitError(f"SEDE VeriFactu devolvió HTTP {r.status_code}: {r.text[:500]}")
        return r.text


# ── Submitters ────────────────────────────────────────────────────────────────


class VerifactuSubmitter(Protocol):
    async def submit(self, db: AsyncSession, *, record, confirmed: bool = False) -> VerifactuAck: ...


class NoRemissionSubmitter:
    """Modo `no_remission` (default): no-op total — idéntico al comportamiento actual."""

    async def submit(self, db: AsyncSession, *, record, confirmed: bool = False) -> VerifactuAck:
        return VerifactuAck(remitted=False, detail="no remitido (modo no_remission)")


class PreproduccionSubmitter:
    """Genera+valida el XML y, SOLO con `confirmed=True`, lo firma con el cert del tenant y lo
    envía. Sin `confirmed` → dry-run (sin POST). Sin cert/firma real → aborta (no finge)."""

    def __init__(
        self,
        transport: VerifactuTransport | None = None,
        environment: str = "preproduccion",
    ) -> None:
        self._transport = transport or HttpxVerifactuTransport()
        self._environment = environment

    async def submit(self, db: AsyncSession, *, record, confirmed: bool = False) -> VerifactuAck:
        # 1) Producir el XML oficial y validarlo contra el XSD (gate de calidad).
        xml = await _rf.generate_alta_xml(db, record=record)
        errors = _rf.validate_verifactu_xml(xml)
        if errors:
            raise VerifactuSubmitError(f"XML VeriFactu inválido contra XSD oficial: {errors[:3]}")

        # 2) Sin confirmación explícita NO se remite (máxima cautela: nunca POST por defecto).
        if not confirmed:
            return VerifactuAck(
                remitted=False,
                dry_run=True,
                detail="dry-run: XML generado y validado contra XSD; NO remitido (confirmed=False)",
            )

        # 2.5) Guard de cumplimiento: NUNCA remitir a la AEAT con el NIF del SIF
        # (productor del software) en placeholder. RD 1007/2023 + Orden HAC/1177/2024
        # exigen el NIF real del productor homologado en `SistemaInformatico`. Sin
        # esto, `default_sistema_informatico()` cae a "B00000000" y se firmaría/enviaría
        # un registro con un NIF ficticio (sanción AEAT). Solo aplica al envío real
        # (confirmed=True); el dry-run de arriba sigue permitido para validar el XML.
        sif_nif = (_rf.default_sistema_informatico().nif or "").strip().upper()
        if not sif_nif or sif_nif == "B00000000":
            raise VerifactuSubmitError(
                "VERIFACTU_SIF_NIF no configurado (placeholder 'B00000000'): no se remite a la "
                "AEAT con el NIF del productor de software ficticio. Configura VERIFACTU_SIF_NIF "
                "con el NIF real del SIF homologado antes de activar el envío en real."
            )

        # 3) Cargar el certificado del tenant (BYO) — sin cert no se envía.
        tenant_id = getattr(record, "tenant_id", None)
        if tenant_id is None:
            raise VerifactuSubmitError("El registro VeriFactu no tiene tenant_id.")
        pfx, password = await _certs.load_decrypted(db, tenant_id)  # CertificateError si no hay

        # 4) Firmar XAdES. Si sale firma *stub* (sin libxmlsec1) NO se envía: no se finge.
        sig = _signer.sign_xades_bes(xml, pfx, password)
        if not sig.signed:
            raise VerifactuSubmitError(
                "Firma no válida para la SEDE (stub: falta libxmlsec1). No se remite sin firma real. "
                + "; ".join(sig.warnings)
            )

        # 5) Enviar (POST mTLS) y parsear el acuse real.
        raw = await self._transport.send(
            signed_xml=sig.signed_xml, pfx=pfx, password=password, environment=self._environment
        )
        return parse_acuse(raw)


async def get_submitter(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    transport: VerifactuTransport | None = None,
) -> VerifactuSubmitter:
    """Elige el submitter por modo del tenant. `no_remission` (default) → no-op."""
    mode = await _mode.get_mode(db, tenant_id=tenant_id)
    if mode != "voluntary":
        return NoRemissionSubmitter()
    return PreproduccionSubmitter(transport=transport)


async def submit_invoice_to_verifactu(
    db: AsyncSession,
    invoice_id: UUID,
    tenant_id: UUID,
    *,
    confirmed: bool = False,
) -> dict:
    """Remite una factura a VeriFactu por el pipeline REAL. Seguro e INACTIVO por defecto.

    Garantías (NUNCA se finge un envío):
      - modo no_remission (default del tenant) → no-op, NO marca enviado.
      - voluntary + confirmed=False → dry-run: valida el XML, NO hace POST, NO marca enviado.
      - voluntary + confirmed=True sin certificado/firma real → aborta SIN enviar.
      - SOLO un acuse REAL 'Correcto' de la AEAT pone verifactu_status='sent'.

    La ruta pasa confirmed=False mientras el envío no esté homologado contra la AEAT:
    queda cableado pero inactivo. Lanza ValueError si la factura no existe.
    """
    from datetime import UTC, datetime

    from sqlalchemy import select

    from app.db.models.billing import Invoice, VerifactuRecord
    from app.services.aeat.certificate_storage import CertificateError

    inv = (
        await db.execute(select(Invoice).where(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id))
    ).scalar_one_or_none()
    if inv is None:
        raise ValueError("Factura no encontrada")

    record = (
        await db.execute(
            select(VerifactuRecord).where(
                VerifactuRecord.invoice_id == invoice_id,
                VerifactuRecord.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if record is None:
        return {
            "invoice_id": str(invoice_id),
            "remitted": False,
            "status": inv.verifactu_status,
            "message": (
                "La factura no tiene registro en la cadena VeriFactu (¿emitida antes "
                "de activar la cadena?). No se ha enviado nada."
            ),
        }

    submitter = await get_submitter(db, tenant_id=tenant_id)
    try:
        ack = await submitter.submit(db, record=record, confirmed=confirmed)
    except (VerifactuSubmitError, CertificateError) as exc:
        # Aborta SIN tocar el estado de la factura: nunca se finge un envío.
        return {
            "invoice_id": str(invoice_id),
            "remitted": False,
            "status": inv.verifactu_status,
            "message": f"No remitido a la AEAT: {exc}",
        }

    if not ack.remitted:
        # no_remission o dry-run: nada enviado, no se marca nada.
        return {
            "invoice_id": str(invoice_id),
            "remitted": False,
            "dry_run": ack.dry_run,
            "status": inv.verifactu_status,
            "message": ack.detail or "No remitido.",
        }

    # Acuse REAL de la AEAT: solo 'Correcto' marca enviado; cualquier otro → error.
    if (ack.estado_envio or "").strip().lower() == "correcto":
        inv.verifactu_status = "sent"
        inv.verifactu_sent_at = datetime.now(tz=UTC)
    else:
        inv.verifactu_status = "error"
    await db.commit()
    return {
        "invoice_id": str(invoice_id),
        "remitted": True,
        "status": inv.verifactu_status,
        "estado_envio": ack.estado_envio,
        "csv": ack.csv,
        "message": f"Acuse AEAT: {ack.estado_envio}",
    }
