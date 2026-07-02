"""Validación del XML antes de firmar (pre-firma).

Dos niveles:
  1. Well-formedness — siempre (stdlib, sin dependencias).
  2. Validación XSD — solo si existe el esquema oficial AEAT en
     `app/services/aeat/xsd/{model_code}.xsd` y `lxml` está instalado.
     Los XSD se descargan de la Sede AEAT (se actualizan anualmente) y
     se depositan en esa carpeta; si faltan, se omite ese nivel.
"""

from __future__ import annotations

import logging
from pathlib import Path
from xml.etree.ElementTree import ParseError, fromstring

_log = logging.getLogger(__name__)

_XSD_DIR = Path(__file__).parent / "xsd"


def validate_xml_pre_signature(xml_str: str, model_code: str) -> list[str]:
    """Devuelve la lista de errores de validación (vacía si el XML es válido)."""
    try:
        fromstring(xml_str.encode("utf-8") if isinstance(xml_str, str) else xml_str)
    except ParseError as e:
        return [f"XML mal formado: {e}"]

    xsd_path = _XSD_DIR / f"{model_code}.xsd"
    if not xsd_path.exists():
        _log.debug("Sin XSD local para modelo %s; se omite validación de esquema.", model_code)
        return []

    try:
        from lxml import etree
    except ImportError:
        _log.warning("lxml no instalado; se omite validación XSD del modelo %s.", model_code)
        return []

    try:
        schema = etree.XMLSchema(etree.parse(str(xsd_path)))
        doc = etree.fromstring(xml_str.encode("utf-8") if isinstance(xml_str, str) else xml_str)
    except (etree.XMLSchemaParseError, etree.XMLSyntaxError) as e:
        return [f"Error preparando validación XSD: {e}"]

    if schema.validate(doc):
        return []
    return [str(err) for err in schema.error_log]
