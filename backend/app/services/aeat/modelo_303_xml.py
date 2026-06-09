"""Generador de XML auxiliar del Modelo 303.

NOTA IMPORTANTE: este XML NO es el formato oficial que firma y envía la SEDE
de la AEAT (eso es un esquema XAdES complejo que requiere certificado digital
del declarante). Esto es un **fichero auxiliar legible por humanos y máquinas**
con TODAS las casillas calculadas. Sirve para:

  1. Revisar todos los importes en un formato estructurado.
  2. Adjuntarlo al expediente que el usuario presenta él mismo en la SEDE.
  3. Ser el insumo del envío real cuando se implemente Fase C
     (presentación electrónica con XAdES).

Estructura: raíz <Modelo303> con metadatos del declarante + lista de <Casilla>.
"""

from __future__ import annotations

from xml.etree.ElementTree import Element, SubElement, tostring

from app.services.aeat.casillas_303 import Casilla303


def build_modelo_303_xml(
    tenant_name: str,
    tenant_nif: str,
    year: int,
    quarter: int,
    casillas: list[Casilla303],
) -> str:
    """Genera el XML auxiliar del 303.

    Returns
    -------
    str
        XML como string UTF-8.
    """
    root = Element("Modelo303", attrib={
        "version": "1.0",
        "ejercicio": str(year),
        "periodo": f"{quarter}T",
        "generador": "AutomatizaCore",
        "tipo": "auxiliar",  # explícito: no es envío oficial
    })

    decl = SubElement(root, "Declarante")
    SubElement(decl, "NIF").text = tenant_nif or ""
    SubElement(decl, "RazonSocial").text = tenant_name or ""

    cas_root = SubElement(root, "Casillas")
    for c in casillas:
        cas = SubElement(cas_root, "Casilla", attrib={
            "codigo": c.codigo,
            "editable": "true" if c.editable else "false",
        })
        SubElement(cas, "Descripcion").text = c.descripcion
        SubElement(cas, "Valor").text = f"{float(c.valor):.2f}"
        if c.nota:
            SubElement(cas, "Nota").text = c.nota

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(root, encoding="unicode")
