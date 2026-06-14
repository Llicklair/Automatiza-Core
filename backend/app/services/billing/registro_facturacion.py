"""VeriFactu — generación del XML `RegFactuSistemaFacturacion`.

RD 1007/2023 + Orden HAC/1177/2024. Construye el XML oficial de la AEAT para un
`RegistroAlta` o `RegistroAnulacion`, reutilizando los campos canónicos que ya se
hashearon en `verifactu_chain` (la `Huella` del XML DEBE coincidir con el
`payload_canonico` almacenado — por eso parseamos ese payload en vez de recomponer
los valores, que podrían divergir).

Esquema verificado contra los XSD oficiales en `services/aeat/xsd/`
(ver `tasks/verifactu_xsd_reference.md`). Detalles que rompen si se ignoran:
  - El targetNamespace NO lleva versión: `.../tike/cont/ws/...` (no `tikeV1.0`).
  - `RegistroAlta`/`RegistroAnulacion` y TODOS sus hijos viven en el namespace
    `sf` (SuministroInformacion); solo la raíz, `Cabecera` y `RegistroFactura`
    son `sfLR` (SuministroLR).
  - Orden de elementos estricto (ver el orden de los `_txt`/`SubElement` abajo).
  - Fechas en `DD-MM-YYYY`; `IdSistemaInformatico` máx 2 caracteres.

El ENVÍO real a la SEDE (mTLS + certificado + firma) es otra capa
(`services/aeat/sede_client`); aquí solo se PRODUCE el XML.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Optional
from xml.etree.ElementTree import Element, SubElement, register_namespace, tostring

from app.services.billing.verifactu_chain import _fmt_fecha_expedicion, _fmt_importe

if TYPE_CHECKING:  # pragma: no cover
    from app.db.models.billing import Invoice, VerifactuRecord

# Namespaces oficiales (targetNamespace literal — SIN `V1.0` en el path).
NS_LR = (
    "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/"
    "aplicaciones/es/aeat/tike/cont/ws/SuministroLR.xsd"
)
NS_SF = (
    "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/"
    "aplicaciones/es/aeat/tike/cont/ws/SuministroInformacion.xsd"
)

register_namespace("sfLR", NS_LR)
register_namespace("sf", NS_SF)

_IDVERSION = "1.0"
_TIPO_HUELLA_SHA256 = "01"
_IMPUESTO_IVA = "01"
_CLAVE_REGIMEN_GENERAL = "01"
_CALIFICACION_SUJETA_NO_EXENTA = "S1"
_MODEL_CODE = "SuministroLR"  # nombre del XSD raíz en services/aeat/xsd/


# ── Identificación del SIF (este software) ──────────────────────────────────


@dataclass(frozen=True)
class SistemaInformatico:
    """Identificación del SIF (este software) que exige VeriFactu.

    `id_sistema` está limitado a 2 caracteres por el XSD (`TextMax2Type`).
    `nif` es el NIF del PRODUCTOR del software (no el del tenant emisor).
    """

    nombre_razon: str
    nif: str
    nombre_sistema: str
    id_sistema: str
    version: str
    numero_instalacion: str
    solo_verifactu: str = "S"
    multi_ot: str = "N"
    indicador_multiples_ot: str = "N"


def default_sistema_informatico() -> SistemaInformatico:
    """SIF por defecto de AutomatizaCore, sobreescribible por settings.

    ⚠️ `nif` es un PLACEHOLDER: antes de presentar a la AEAT en real debe ser el
    NIF del productor del software (`VERIFACTU_SIF_NIF` en settings/.env).
    """
    from app.core.config import settings

    def _s(attr: str, default: str) -> str:
        return str(getattr(settings, attr, None) or default)

    return SistemaInformatico(
        nombre_razon=_s("VERIFACTU_SIF_NOMBRE_RAZON", "AutomatizaCore"),
        nif=_s("VERIFACTU_SIF_NIF", "B00000000"),
        nombre_sistema=_s("VERIFACTU_SIF_NOMBRE_SISTEMA", "AutomatizaCore"),
        id_sistema=_s("VERIFACTU_SIF_ID", "01")[:2],
        version=_s("VERIFACTU_SIF_VERSION", "1.0"),
        numero_instalacion=_s("VERIFACTU_SIF_NUM_INSTALACION", "0001"),
    )


# ── Helpers de bajo nivel ───────────────────────────────────────────────────


def _parse_payload(payload: str) -> dict[str, str]:
    """Descompone la cadena canónica `clave=valor&...` en un dict.

    Usa `partition` (no `split('=')`) por si algún valor llevara `=`.
    """
    out: dict[str, str] = {}
    for part in (payload or "").split("&"):
        if not part:
            continue
        key, _, value = part.partition("=")
        out[key] = value
    return out


def _txt(parent: Element, ns: str, tag: str, value: str) -> Element:
    el = SubElement(parent, f"{{{ns}}}{tag}")
    el.text = value
    return el


def _serialize(root: Element) -> str:
    return tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")


def _fmt_tipo(rate) -> str:
    """`TipoImpositivo` (patrón `\\d{1,3}(\\.\\d{0,2})?`): sin ceros finales.

    21.00 → "21"; 10.50 → "10.5"; 4.00 → "4".
    """
    d = Decimal(rate if rate is not None else 0)
    s = f"{d:.2f}".rstrip("0").rstrip(".")
    return s or "0"


def _cabecera(root: Element, emisor_nombre: str, emisor_nif: str) -> None:
    cab = SubElement(root, f"{{{NS_LR}}}Cabecera")
    obl = SubElement(cab, f"{{{NS_SF}}}ObligadoEmision")
    _txt(obl, NS_SF, "NombreRazon", (emisor_nombre or "")[:120])
    _txt(obl, NS_SF, "NIF", emisor_nif)


def _sistema_informatico(parent: Element, s: SistemaInformatico) -> None:
    si = SubElement(parent, f"{{{NS_SF}}}SistemaInformatico")
    _txt(si, NS_SF, "NombreRazon", s.nombre_razon[:120])
    _txt(si, NS_SF, "NIF", s.nif)  # CHOICE NIF | IDOtro → usamos NIF (productor ES)
    _txt(si, NS_SF, "NombreSistemaInformatico", s.nombre_sistema[:30])
    _txt(si, NS_SF, "IdSistemaInformatico", s.id_sistema[:2])
    _txt(si, NS_SF, "Version", s.version[:50])
    _txt(si, NS_SF, "NumeroInstalacion", s.numero_instalacion[:100])
    _txt(si, NS_SF, "TipoUsoPosibleSoloVerifactu", s.solo_verifactu)
    _txt(si, NS_SF, "TipoUsoPosibleMultiOT", s.multi_ot)
    _txt(si, NS_SF, "IndicadorMultiplesOT", s.indicador_multiples_ot)


def _encadenamiento(parent: Element, huella_anterior: Optional[str], prev_record) -> None:
    """`Encadenamiento`: PrimerRegistro="S" o RegistroAnterior (4 campos).

    Si hay `huella_anterior`, el `RegistroAnterior` necesita la IDENTIDAD de la
    factura previa (NIF/serie/fecha), que NO está en la huella → exige
    `prev_record` (el `VerifactuRecord` inmediatamente anterior del tenant).
    """
    enc = SubElement(parent, f"{{{NS_SF}}}Encadenamiento")
    if not huella_anterior:
        _txt(enc, NS_SF, "PrimerRegistro", "S")
        return
    if prev_record is None:
        raise ValueError(
            "RegistroAnterior requiere prev_record: hay huella_anterior pero no se "
            "pasó el registro previo para identificar su factura."
        )
    ra = SubElement(enc, f"{{{NS_SF}}}RegistroAnterior")
    _txt(ra, NS_SF, "IDEmisorFactura", prev_record.nif_emisor)
    _txt(ra, NS_SF, "NumSerieFactura", prev_record.numero_factura)
    _txt(ra, NS_SF, "FechaExpedicionFactura", _fmt_fecha_expedicion(prev_record.fecha_emision))
    _txt(ra, NS_SF, "Huella", huella_anterior)


# ── Desglose ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class _Detalle:
    tipo: Optional[str]   # TipoImpositivo (ej. "21"); None si no aplica
    base: str             # BaseImponibleOimporteNoSujeto
    cuota: Optional[str]  # CuotaRepercutida


def _detalles(invoice, lines) -> list[_Detalle]:
    """Construye los `DetalleDesglose` (máx 12) agrupando por tipo de IVA.

    Con líneas: una entrada por cada `tax_percentage` distinto. Sin líneas: una
    sola entrada desde los totales de cabecera (tipo efectivo = cuota/base).
    """
    if lines:
        groups: dict[str, list[tuple[Decimal, Decimal]]] = {}
        for ln in lines:
            rate = Decimal(getattr(ln, "tax_percentage", None) or 0)
            qty = Decimal(getattr(ln, "quantity", None) or 0)
            unit = Decimal(getattr(ln, "unit_price", None) or 0)
            groups.setdefault(_fmt_tipo(rate), []).append((rate, qty * unit))
        detalles: list[_Detalle] = []
        for tipo, items in groups.items():
            base_sum = sum((b for _, b in items), Decimal("0"))
            rate = items[0][0]
            cuota = base_sum * rate / Decimal("100")
            detalles.append(
                _Detalle(tipo=tipo, base=_fmt_importe(base_sum), cuota=_fmt_importe(cuota))
            )
        if detalles:
            return detalles[:12]

    base = Decimal(invoice.amount_base if invoice.amount_base is not None else 0)
    cuota = Decimal(invoice.tax_amount if invoice.tax_amount is not None else 0)
    tipo = None
    if base > 0 and cuota > 0:
        tipo = _fmt_tipo((cuota / base * Decimal("100")).quantize(Decimal("0.01")))
    return [_Detalle(tipo=tipo, base=_fmt_importe(base), cuota=_fmt_importe(cuota) if cuota else None)]


def _desglose(parent: Element, invoice, lines) -> None:
    desg = SubElement(parent, f"{{{NS_SF}}}Desglose")
    for det in _detalles(invoice, lines):
        d = SubElement(desg, f"{{{NS_SF}}}DetalleDesglose")
        _txt(d, NS_SF, "Impuesto", _IMPUESTO_IVA)
        _txt(d, NS_SF, "ClaveRegimen", _CLAVE_REGIMEN_GENERAL)
        _txt(d, NS_SF, "CalificacionOperacion", _CALIFICACION_SUJETA_NO_EXENTA)
        if det.tipo is not None:
            _txt(d, NS_SF, "TipoImpositivo", det.tipo)
        _txt(d, NS_SF, "BaseImponibleOimporteNoSujeto", det.base)
        if det.cuota is not None:
            _txt(d, NS_SF, "CuotaRepercutida", det.cuota)


def _descripcion(invoice, lines) -> str:
    if lines:
        parts = [str(getattr(ln, "description", "") or "").strip() for ln in lines]
        joined = "; ".join(p for p in parts if p)
        if joined:
            return joined
    return "Operación de venta de bienes y/o servicios"


# ── Builders públicos ───────────────────────────────────────────────────────


def build_registro_alta_xml(
    *,
    record: "VerifactuRecord",
    invoice: "Invoice",
    emisor_nombre: str,
    lines=None,
    sistema: Optional[SistemaInformatico] = None,
    prev_record: Optional["VerifactuRecord"] = None,
    descripcion: Optional[str] = None,
) -> str:
    """Genera el XML `RegFactuSistemaFacturacion` con un `RegistroAlta`.

    Reutiliza `record.payload_canonico` (campos exactos hasheados) y `record.huella`,
    de modo que el XML es consistente con la cadena por construcción.
    """
    p = _parse_payload(record.payload_canonico)
    sistema = sistema or default_sistema_informatico()

    root = Element(f"{{{NS_LR}}}RegFactuSistemaFacturacion")
    _cabecera(root, emisor_nombre, p["IDEmisorFactura"])
    rf = SubElement(root, f"{{{NS_LR}}}RegistroFactura")
    alta = SubElement(rf, f"{{{NS_SF}}}RegistroAlta")

    _txt(alta, NS_SF, "IDVersion", _IDVERSION)
    idf = SubElement(alta, f"{{{NS_SF}}}IDFactura")
    _txt(idf, NS_SF, "IDEmisorFactura", p["IDEmisorFactura"])
    _txt(idf, NS_SF, "NumSerieFactura", p["NumSerieFactura"])
    _txt(idf, NS_SF, "FechaExpedicionFactura", p["FechaExpedicionFactura"])
    _txt(alta, NS_SF, "NombreRazonEmisor", (emisor_nombre or "")[:120])
    _txt(alta, NS_SF, "TipoFactura", p["TipoFactura"])
    _txt(alta, NS_SF, "DescripcionOperacion", (descripcion or _descripcion(invoice, lines))[:500])
    _desglose(alta, invoice, lines)
    _txt(alta, NS_SF, "CuotaTotal", p["CuotaTotal"])
    _txt(alta, NS_SF, "ImporteTotal", p["ImporteTotal"])
    _encadenamiento(alta, record.huella_anterior, prev_record)
    _sistema_informatico(alta, sistema)
    _txt(alta, NS_SF, "FechaHoraHusoGenRegistro", p["FechaHoraHusoGenRegistro"])
    _txt(alta, NS_SF, "TipoHuella", _TIPO_HUELLA_SHA256)
    _txt(alta, NS_SF, "Huella", record.huella)
    return _serialize(root)


def build_registro_anulacion_xml(
    *,
    emisor_nombre: str,
    emisor_nif: str,
    num_serie: str,
    fecha_expedicion: str,
    huella: str,
    fecha_hora_gen: str,
    huella_anterior: Optional[str] = None,
    prev_record: Optional["VerifactuRecord"] = None,
    sistema: Optional[SistemaInformatico] = None,
) -> str:
    """Genera el XML `RegFactuSistemaFacturacion` con un `RegistroAnulacion`.

    Toma campos explícitos (la anulación no se persiste como `VerifactuRecord`
    todavía). `fecha_expedicion` en `DD-MM-YYYY`, `fecha_hora_gen` ISO con huso.
    """
    sistema = sistema or default_sistema_informatico()

    root = Element(f"{{{NS_LR}}}RegFactuSistemaFacturacion")
    _cabecera(root, emisor_nombre, emisor_nif)
    rf = SubElement(root, f"{{{NS_LR}}}RegistroFactura")
    an = SubElement(rf, f"{{{NS_SF}}}RegistroAnulacion")

    _txt(an, NS_SF, "IDVersion", _IDVERSION)
    idf = SubElement(an, f"{{{NS_SF}}}IDFactura")
    _txt(idf, NS_SF, "IDEmisorFacturaAnulada", emisor_nif)
    _txt(idf, NS_SF, "NumSerieFacturaAnulada", num_serie)
    _txt(idf, NS_SF, "FechaExpedicionFacturaAnulada", fecha_expedicion)
    _encadenamiento(an, huella_anterior, prev_record)
    _sistema_informatico(an, sistema)
    _txt(an, NS_SF, "FechaHoraHusoGenRegistro", fecha_hora_gen)
    _txt(an, NS_SF, "TipoHuella", _TIPO_HUELLA_SHA256)
    _txt(an, NS_SF, "Huella", huella)
    return _serialize(root)


# ── Validación + carga desde DB ─────────────────────────────────────────────


def validate_verifactu_xml(xml_str: str) -> list[str]:
    """Valida el XML contra el XSD oficial `SuministroLR.xsd`.

    Dos niveles: (1) well-formedness — siempre (stdlib). (2) XSD — si están los
    esquemas en `services/aeat/xsd/` y `lxml`. Offline-safe: un resolver sirve el
    `xmldsig-core-schema.xsd` local (lo importa `SuministroInformacion.xsd` por
    URL absoluta) cuando existe; si no, cae al comportamiento por defecto.
    Devuelve la lista de errores (vacía = válido).
    """
    from xml.etree.ElementTree import ParseError
    from xml.etree.ElementTree import fromstring as _et_fromstring

    raw = xml_str.encode("utf-8") if isinstance(xml_str, str) else xml_str
    try:
        _et_fromstring(raw)
    except ParseError as e:
        return [f"XML mal formado: {e}"]

    xsd_dir = Path(__file__).resolve().parents[1] / "aeat" / "xsd"
    xsd_path = xsd_dir / f"{_MODEL_CODE}.xsd"
    if not xsd_path.exists():
        return []
    try:
        from lxml import etree
    except ImportError:
        return []

    class _LocalResolver(etree.Resolver):
        def resolve(self, url, pubid, context):
            if url and url.rstrip("/").endswith("xmldsig-core-schema.xsd"):
                local = xsd_dir / "xmldsig-core-schema.xsd"
                if local.exists():
                    return self.resolve_filename(str(local), context)
            return None  # default: relativos vía path del XSD, absolutos vía red

    try:
        parser = etree.XMLParser()
        parser.resolvers.add(_LocalResolver())
        schema = etree.XMLSchema(etree.parse(str(xsd_path), parser))
        doc = etree.fromstring(raw)
    except (etree.XMLSchemaParseError, etree.XMLSyntaxError) as e:
        return [f"Error preparando validación XSD: {e}"]

    return [] if schema.validate(doc) else [str(err) for err in schema.error_log]


async def generate_alta_xml(db, *, record: "VerifactuRecord", sistema=None) -> str:
    """Carga factura/emisor/registro-previo y construye el XML del `RegistroAlta`."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.db.models.auth import Tenant
    from app.db.models.billing import Invoice, VerifactuRecord

    res = await db.execute(
        select(Invoice).options(selectinload(Invoice.lines)).where(Invoice.id == record.invoice_id)
    )
    invoice = res.scalar_one()
    tenant = await db.get(Tenant, record.tenant_id)

    prev_record = None
    if record.huella_anterior:
        pr = await db.execute(
            select(VerifactuRecord).where(
                VerifactuRecord.tenant_id == record.tenant_id,
                VerifactuRecord.huella == record.huella_anterior,
            )
        )
        prev_record = pr.scalar_one_or_none()

    return build_registro_alta_xml(
        record=record,
        invoice=invoice,
        emisor_nombre=tenant.name if tenant else "",
        lines=list(invoice.lines),
        sistema=sistema,
        prev_record=prev_record,
    )
