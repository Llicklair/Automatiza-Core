"""Costura del ENVÍO VeriFactu a la AEAT — preparada, NO conectada al flujo vivo.

Estado (2026-06-19): el FORMATO ya está hecho y verificado — el XML `RegistroAlta`/
`RegistroAnulacion` valida contra el XSD oficial (`registro_facturacion`), la huella va
encadenada y el QR existe. Esta capa prepara el ENVÍO real al web service de la AEAT
**sin implementarlo a ciegas**:

  - El transporte real (firma XAdES + POST SOAP con mTLS usando el certificado del tenant,
    modelo BYO) queda como `NotImplementedError` hasta disponer de **certificado + entorno de
    preproducción** de la AEAT. El endpoint está marcado *POR CONFIRMAR*.
  - NADA se envía ni se fabrica: el `CSV`/acuse SOLO proviene de una respuesta REAL parseada
    (`parse_acuse`). En `dry-run` (sin `confirmed`) no se hace POST.
  - El modo por defecto (`no_remission`) es un **no-op idéntico al comportamiento actual**.

Este módulo NO se invoca todavía desde la emisión de facturas (ver el punto de enganche
documentado en `tasks/verifactu_envio_spec.md`). Es la "costura" lista para enchufar cuando
haya certificado, manteniendo máxima cautela: el envío real está gated por `confirmed=True`
+ certificado + preproducción.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.billing import registro_facturacion as _rf
from app.services.billing import verifactu_mode as _mode

# Endpoints del web service VeriFactu (Suministro de Registros de Facturación).
# POR CONFIRMAR contra el WSDL oficial de la AEAT con un certificado de preproducción:
# las URLs/sobre SOAP no se han validado contra el entorno real (no hay cert todavía).
VERIFACTU_ENDPOINTS = {
    # candidato a confirmar (preproducción TIKE-CONT). NO usar sin verificar.
    "preproduccion": "https://prewww1.aeat.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP",
    "produccion": None,  # se rellenará tras homologar en preproducción
}


class VerifactuSubmitError(Exception):
    """Error de la costura de envío (XML inválido, acuse irreconocible, etc.)."""


# ── Acuse (RespuestaRegFactuSistemaFacturacion, RespuestaSuministro.xsd) ──────


@dataclass(frozen=True)
class VerifactuLineAck:
    """Estado por registro dentro del acuse (RespuestaLinea)."""

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
    """Local-name de un tag (ignora el namespace) para parsear robusto a prefijos/SOAP."""
    return tag.rsplit("}", 1)[-1]


def _direct_text(parent: ET.Element, name: str) -> str | None:
    for child in parent:
        if _ln(child.tag) == name:
            return (child.text or "").strip() or None
    return None


def parse_acuse(response_xml: str) -> VerifactuAck:
    """Parsea el cuerpo `RespuestaRegFactuSistemaFacturacion` (puede venir envuelto en SOAP).

    Pure: sin red ni BD. Localiza el nodo por local-name, así tolera prefijos y el sobre SOAP.
    """
    try:
        root = ET.fromstring(response_xml)
    except ET.ParseError as e:
        raise VerifactuSubmitError(f"Respuesta VeriFactu no es XML válido: {e}") from e

    resp = root if _ln(root.tag) == "RespuestaRegFactuSistemaFacturacion" else next(
        (e for e in root.iter() if _ln(e.tag) == "RespuestaRegFactuSistemaFacturacion"),
        None,
    )
    if resp is None:
        raise VerifactuSubmitError(
            "Respuesta sin RespuestaRegFactuSistemaFacturacion (¿error SOAP / fault?)"
        )

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


# ── Transporte (la parte cert-gated; hoy NotImplementedError) ─────────────────


class VerifactuTransport(Protocol):
    """Transporte del envío. La impl real firma (XAdES) y hace POST SOAP con mTLS.

    Devuelve el cuerpo XML crudo de `RespuestaRegFactuSistemaFacturacion`.
    """

    async def post(self, *, xml: str, environment: str, confirmed: bool) -> str: ...


class _RealVerifactuTransport:
    """Transporte REAL — pendiente (requiere certificado + preproducción).

    No implementado a ciegas: firmar con XAdES y POST SOAP mTLS con el cert del tenant (BYO),
    y validar contra el entorno de pruebas de la AEAT. Ver `tasks/verifactu_envio_spec.md`.
    """

    async def post(self, *, xml: str, environment: str, confirmed: bool) -> str:
        raise NotImplementedError(
            "Transporte real VeriFactu pendiente: falta firmar (XAdES) y enviar (POST SOAP "
            f"mTLS) al endpoint de {environment} "
            f"({VERIFACTU_ENDPOINTS.get(environment) or 'POR CONFIRMAR'}). "
            "Requiere certificado del tenant (modelo BYO) y validación contra AEAT "
            "preproducción. Ver tasks/verifactu_envio_spec.md."
        )


# ── Submitters ────────────────────────────────────────────────────────────────


class VerifactuSubmitter(Protocol):
    async def submit(
        self, db: AsyncSession, *, record, confirmed: bool = False
    ) -> VerifactuAck: ...


class NoRemissionSubmitter:
    """Modo `no_remission` (default): no-op total — idéntico al comportamiento actual."""

    async def submit(
        self, db: AsyncSession, *, record, confirmed: bool = False
    ) -> VerifactuAck:
        return VerifactuAck(
            remitted=False,
            detail="no remitido (modo no_remission)",
        )


class PreproduccionSubmitter:
    """Genera+valida el XML y, SOLO con `confirmed=True` y transporte real, lo enviaría.

    Cautela: sin `confirmed` no se llama al transporte (no hay POST posible). Sin transporte
    real configurado, `confirmed=True` levanta NotImplementedError (no se finge un envío).
    """

    def __init__(
        self,
        transport: VerifactuTransport | None = None,
        environment: str = "preproduccion",
    ) -> None:
        self._transport = transport
        self._environment = environment

    async def submit(
        self, db: AsyncSession, *, record, confirmed: bool = False
    ) -> VerifactuAck:
        # 1) Producir el XML oficial y validarlo contra el XSD (gate de calidad).
        xml = await _rf.generate_alta_xml(db, record=record)
        errors = _rf.validate_verifactu_xml(xml)
        if errors:
            raise VerifactuSubmitError(
                f"XML VeriFactu inválido contra XSD oficial: {errors[:3]}"
            )

        # 2) Sin confirmación explícita NO se remite (máxima cautela: nunca POST por defecto).
        if not confirmed:
            return VerifactuAck(
                remitted=False,
                dry_run=True,
                detail="dry-run: XML generado y validado contra XSD; NO remitido (confirmed=False)",
            )

        # 3) Con confirmación: exige transporte. El real está pendiente (cert+preproducción).
        if self._transport is None:
            raise NotImplementedError(
                "Envío real VeriFactu no implementado (sin transporte/certificado). "
                "Ver tasks/verifactu_envio_spec.md."
            )
        raw = await self._transport.post(
            xml=xml, environment=self._environment, confirmed=confirmed
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
    return PreproduccionSubmitter(transport=transport or _RealVerifactuTransport())
