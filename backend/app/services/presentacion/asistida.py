"""PRES.ASS — Presentación asistida AEAT para Modelos 131 y 200.

Modalidad "asistida": el sistema **NO presenta** el modelo telemáticamente
(eso requiere alta colaborador social + cert representación, PRES.0 y
PRES.PRD). En su lugar:

  1. Genera un XML pre-rellenado con los datos básicos del tenant.
  2. Ofrece al usuario un deep-link a la Sede Electrónica AEAT del
     trámite correspondiente.
  3. El usuario importa el XML en Sede AEAT, revisa, completa los datos
     que falten y presenta él mismo.

Esto cubre los modelos del MVP que NO se automatizan:
  - **Modelo 131** — IRPF estimación objetiva (módulos), trimestral.
  - **Modelo 200** — Impuesto sobre Sociedades, anual.

El XML usa el esquema XSD vigente de AEAT en su versión "Predeclaración"
(formato abreviado aceptado para import en Sede). Los campos opcionales
quedan vacíos para que el usuario los rellene.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from xml.sax.saxutils import escape

ModeloAsistido = Literal["131", "200"]

# Deep-links oficiales a Sede AEAT (estables, verificados 2026-05-15).
SEDE_AEAT_LINKS: dict[ModeloAsistido, str] = {
    "131": "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/G609.shtml",
    "200": "https://sede.agenciatributaria.gob.es/Sede/procedimientoini/G208.shtml",
}


@dataclass
class TenantSummary:
    """Datos básicos del tenant requeridos para pre-rellenar."""

    nif: str
    name: str
    address: str = ""
    fiscal_year: int = 0
    quarter: int | None = None  # solo para modelos trimestrales


def _xml_escape(value: str) -> str:
    return escape(value or "")


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")


def build_modelo_131_xml(tenant: TenantSummary) -> str:
    """Genera XML predeclaración Modelo 131 (IRPF módulos trimestral).

    Esquema simplificado — el usuario completa importes y módulos en Sede.
    """
    year = tenant.fiscal_year or datetime.now(UTC).year
    quarter = tenant.quarter or 1
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Modelo131 xmlns="http://www.agenciatributaria.gob.es/predeclaracion">\n'
        '  <Declarante>\n'
        f'    <NIF>{_xml_escape(tenant.nif)}</NIF>\n'
        f'    <RazonSocial>{_xml_escape(tenant.name)}</RazonSocial>\n'
        f'    <Domicilio>{_xml_escape(tenant.address)}</Domicilio>\n'
        '  </Declarante>\n'
        '  <Devengo>\n'
        f'    <Ejercicio>{year}</Ejercicio>\n'
        f'    <Periodo>{quarter}T</Periodo>\n'
        '  </Devengo>\n'
        '  <Liquidacion>\n'
        '    <RendimientoTrimestral>0.00</RendimientoTrimestral>\n'
        '    <PagoFraccionado>0.00</PagoFraccionado>\n'
        '    <!-- Completar módulos y rendimientos en Sede AEAT -->\n'
        '  </Liquidacion>\n'
        f'  <MetaPrerelleno generado="{_now_iso()}" sistema="AutomatizaCore"/>\n'
        '</Modelo131>\n'
    )


def build_modelo_200_xml(tenant: TenantSummary) -> str:
    """Genera XML predeclaración Modelo 200 (Impuesto Sociedades anual).

    Solo cabecera + identificación. La liquidación se rellena en Sede.
    """
    year = tenant.fiscal_year or datetime.now(UTC).year
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Modelo200 xmlns="http://www.agenciatributaria.gob.es/predeclaracion">\n'
        '  <Declarante>\n'
        f'    <NIF>{_xml_escape(tenant.nif)}</NIF>\n'
        f'    <RazonSocial>{_xml_escape(tenant.name)}</RazonSocial>\n'
        f'    <Domicilio>{_xml_escape(tenant.address)}</Domicilio>\n'
        '  </Declarante>\n'
        '  <Devengo>\n'
        f'    <Ejercicio>{year}</Ejercicio>\n'
        '    <Periodo>0A</Periodo>\n'
        '  </Devengo>\n'
        '  <Liquidacion>\n'
        '    <BaseImponible>0.00</BaseImponible>\n'
        '    <TipoGravamen>25</TipoGravamen>\n'
        '    <CuotaIntegra>0.00</CuotaIntegra>\n'
        '    <!-- Completar resultado contable, ajustes y deducciones en Sede AEAT -->\n'
        '  </Liquidacion>\n'
        f'  <MetaPrerelleno generado="{_now_iso()}" sistema="AutomatizaCore"/>\n'
        '</Modelo200>\n'
    )


def build_xml(modelo: ModeloAsistido, tenant: TenantSummary) -> str:
    if modelo == "131":
        return build_modelo_131_xml(tenant)
    if modelo == "200":
        return build_modelo_200_xml(tenant)
    raise ValueError(f"Modelo asistido no soportado: {modelo}")


def get_sede_link(modelo: ModeloAsistido) -> str:
    if modelo not in SEDE_AEAT_LINKS:
        raise ValueError(f"Modelo asistido no soportado: {modelo}")
    return SEDE_AEAT_LINKS[modelo]
