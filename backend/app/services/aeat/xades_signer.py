"""Firma XAdES-BES enveloped sobre el XML de modelos AEAT.

Esta es la pieza crítica que la SEDE AEAT exige para aceptar el envío.
Requiere `signxml` + `xmlsec` (libxmlsec1 nativo). Si la lib no está
instalada, devolvemos un XML envuelto en una etiqueta `<UnsignedDraft>` y
marcamos el resultado como `signed=False` — el orchestrator decide qué hacer.

En desarrollo (sin libxmlsec1) puede usarse la versión stub para iterar el
flujo end-to-end sin firmar de verdad. En producción se exige firma real.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

_log = logging.getLogger(__name__)


@dataclass
class SignResult:
    signed_xml: str
    signed: bool        # False si fue stub
    method: str         # 'xades-bes' | 'stub'
    warnings: list[str]


class SigningError(RuntimeError):
    pass


def _is_available() -> bool:
    try:
        import signxml  # noqa
        import xmlsec   # noqa: F401
        return True
    except ImportError:
        return False


def sign_xades_bes(xml_str: str, pfx_bytes: bytes, password: str) -> SignResult:
    """Intenta firmar con XAdES-BES. Si no hay libs, devuelve stub.

    No lanza en modo stub — el caller decide cómo proceder según
    `signed` y `warnings`. Lanza solo si los datos son inválidos.
    """
    if not xml_str or not xml_str.strip().startswith("<"):
        raise SigningError("XML vacío o malformado.")

    warnings: list[str] = []

    if not _is_available():
        warnings.append(
            "Firma stub: signxml/xmlsec no instalados. Este XML NO es válido para la SEDE AEAT."
        )
        wrapped = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<UnsignedDraft generator="AutomatizaPyme" note="stub-no-xmlsec">\n'
            f"{xml_str.lstrip(chr(10)).lstrip()}\n"
            "</UnsignedDraft>"
        )
        return SignResult(signed_xml=wrapped, signed=False, method="stub", warnings=warnings)

    # Camino real (cuando libs están instaladas)
    try:
        from signxml import XMLSigner, methods
        from cryptography.hazmat.primitives.serialization import pkcs12
        from lxml import etree
    except ImportError as e:
        raise SigningError(f"Falta dependencia en runtime: {e}") from e

    try:
        priv_key, cert, ca_chain = pkcs12.load_key_and_certificates(
            pfx_bytes, password.encode("utf-8") if password else None,
        )
    except Exception as e:
        raise SigningError(f"No se pudo cargar el PFX: {e}") from e

    try:
        # Parsear XML
        root = etree.fromstring(xml_str.encode("utf-8") if isinstance(xml_str, str) else xml_str)
        signer = XMLSigner(
            method=methods.enveloped,
            signature_algorithm="rsa-sha256",
            digest_algorithm="sha256",
        )
        signed_root = signer.sign(root, key=priv_key, cert=cert)
        signed_bytes = etree.tostring(signed_root, xml_declaration=True, encoding="UTF-8")
        return SignResult(
            signed_xml=signed_bytes.decode("utf-8"),
            signed=True,
            method="xades-bes",
            warnings=warnings,
        )
    except Exception as e:
        raise SigningError(f"Error al firmar XML: {e}") from e
