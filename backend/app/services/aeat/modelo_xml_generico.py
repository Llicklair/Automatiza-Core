"""Generador XML auxiliar genérico para modelos AEAT (no-303).

Misma filosofía que `modelo_303_xml`: este XML NO sigue el XSD oficial al
100% — sirve como insumo auditable y para que el orquestador Fase C tenga
un payload firmable. Para envío real a producción cada modelo requiere su
esquema oficial publicado por la AEAT.

Convención: cada modelo tiene su función `build_modelo_{NN}_data` en
`services.reports.modelos_aeat` y devuelve un dict con cifras precalculadas.
Aquí los serializamos a XML preservando la estructura del dict.
"""

from __future__ import annotations

from xml.etree.ElementTree import Element, SubElement, tostring


def _to_xml(parent: Element, name: str, value) -> None:
    """Convierte valor Python a sub-elemento XML, con soporte para listas y dicts."""
    if value is None:
        SubElement(parent, name).text = ""
        return
    if isinstance(value, dict):
        node = SubElement(parent, name)
        for k, v in value.items():
            _to_xml(node, _safe_tag(k), v)
        return
    if isinstance(value, (list, tuple)):
        node = SubElement(parent, name)
        for _i, v in enumerate(value):
            _to_xml(node, "Item", v)
        return
    if isinstance(value, (int, float)):
        SubElement(parent, name).text = (
            f"{value:.2f}" if isinstance(value, float) else str(value)
        )
        return
    if isinstance(value, bool):
        SubElement(parent, name).text = "true" if value else "false"
        return
    SubElement(parent, name).text = str(value)


def _safe_tag(name: str) -> str:
    """Normaliza una clave para que sea un nombre XML válido."""
    s = str(name).strip() or "Campo"
    out = []
    for ch in s:
        if ch.isalnum() or ch in "_-.":
            out.append(ch)
        else:
            out.append("_")
    if out and out[0].isdigit():
        out.insert(0, "_")
    return "".join(out)


def build_modelo_xml_generic(
    modelo: str,
    year: int,
    period: str,
    data: dict,
    tenant_name: str = "",
    tenant_nif: str = "",
) -> str:
    """Genera XML auxiliar para un modelo AEAT a partir del dict pre-calculado."""
    root = Element("Modelo", attrib={
        "codigo": str(modelo),
        "version": "1.0",
        "ejercicio": str(year),
        "periodo": str(period),
        "generador": "AutomatizaCore",
        "tipo": "auxiliar",
    })

    decl = SubElement(root, "Declarante")
    SubElement(decl, "NIF").text = tenant_nif or ""
    SubElement(decl, "RazonSocial").text = tenant_name or ""

    contenido = SubElement(root, "Contenido")
    if isinstance(data, dict):
        # Excluir el bloque tenant si ya lo metimos arriba
        for k, v in data.items():
            if k == "tenant":
                continue
            _to_xml(contenido, _safe_tag(k), v)
    else:
        _to_xml(contenido, "Datos", data)

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(root, encoding="unicode")
