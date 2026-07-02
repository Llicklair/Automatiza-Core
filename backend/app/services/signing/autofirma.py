"""Constructor de URI `afirma://` y parser de respuesta (F3.11).

Protocolo AutoFirma (especificación v1.5+) — del MAP/INTECO. El cliente
AutoFirma se invoca con una URI del estilo:

    afirma://sign?ver=1_5&dat=<base64>&j=true&keystore=...

Donde `dat` es la configuración (formato, algoritmo, retrieverServletUrl,
storageServletUrl, datos del documento). Aquí construimos esa URI a
partir de parámetros tipados; no requiere AutoFirma instalado durante
los tests porque sólo manipulamos strings/base64.

Cuando AutoFirma termina, hace POST al `storageServletUrl` con el
documento firmado. Nuestro endpoint en `routes/signing.py` lo recibe.
"""

from __future__ import annotations

import base64
import hashlib
import json
from enum import Enum
from typing import Any
from urllib.parse import quote


class AutoFirmaError(ValueError):
    """Error de validación al construir/parsear AutoFirma."""


class SignatureFormat(str, Enum):
    PADES = "PAdES"  # PDF
    XADES = "XAdES"  # XML (compat 303, Facturae, etc.)
    CADES = "CAdES"  # binarios genéricos

    @property
    def autofirma_code(self) -> str:
        # AutoFirma usa los identificadores en minúscula
        return self.value.lower()


_DEFAULT_ALGO = "SHA512withRSA"
_VALID_ALGOS = {
    "SHA256withRSA",
    "SHA384withRSA",
    "SHA512withRSA",
}


def file_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_autofirma_uri(
    document_bytes: bytes,
    *,
    signature_format: SignatureFormat,
    storage_servlet_url: str,
    retriever_servlet_url: str,
    session_token: str,
    algorithm: str = _DEFAULT_ALGO,
    visible_signature: bool = False,
) -> tuple[str, str]:
    """Genera la URI `afirma://` para iniciar la firma.

    Devuelve (uri, document_hash). El hash se guarda en `signed_documents`
    para validar la integridad cuando AutoFirma devuelva el firmado.
    """
    if not document_bytes:
        raise AutoFirmaError("Documento vacío.")
    if algorithm not in _VALID_ALGOS:
        raise AutoFirmaError(f"Algoritmo no soportado: {algorithm}")
    if not session_token or len(session_token) < 16:
        raise AutoFirmaError("session_token inválido (mínimo 16 chars).")

    doc_hash = file_sha256(document_bytes)
    doc_b64 = base64.urlsafe_b64encode(document_bytes).decode("ascii")

    config: dict[str, Any] = {
        "operation": "sign",
        "format": signature_format.autofirma_code,
        "algorithm": algorithm,
        "storageServletUrl": storage_servlet_url,
        "retrieverServletUrl": retriever_servlet_url,
        "id": session_token,
        "dat": doc_b64,
    }
    if signature_format == SignatureFormat.PADES:
        config["extraParams"] = "signatureVisible=true" if visible_signature else "signatureVisible=false"

    config_json = json.dumps(config, separators=(",", ":"))
    config_b64 = base64.urlsafe_b64encode(config_json.encode("utf-8")).decode("ascii")

    uri = "afirma://sign?ver=1_5" f"&id={quote(session_token, safe='')}" "&j=true" f"&dat={config_b64}"
    return uri, doc_hash


def parse_autofirma_response(payload: dict | bytes | str) -> dict[str, Any]:
    """Normaliza la respuesta de AutoFirma al callback.

    AutoFirma puede enviar la firma como:
      - JSON con campos {id, data (base64), format, errorType?}
      - body raw base64 (POST text/plain)
      - bytes con el documento firmado directamente

    Devuelve {session_token, signed_bytes, error}. Lanza `AutoFirmaError`
    si el payload no es interpretable.
    """
    if isinstance(payload, dict):
        if payload.get("errorType"):
            raise AutoFirmaError(f"AutoFirma error: {payload['errorType']}")
        data = payload.get("data") or payload.get("dat") or payload.get("signedDoc")
        token = payload.get("id") or payload.get("session_token")
        if not data or not token:
            raise AutoFirmaError("Respuesta JSON sin data/id.")
        try:
            signed = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
        except Exception as e:
            raise AutoFirmaError(f"data no es base64 urlsafe válido: {e}") from e
        return {"session_token": token, "signed_bytes": signed, "error": None}

    if isinstance(payload, str):
        try:
            signed = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        except Exception as e:
            raise AutoFirmaError(f"body no es base64: {e}") from e
        return {"session_token": None, "signed_bytes": signed, "error": None}

    if isinstance(payload, (bytes, bytearray)):
        return {"session_token": None, "signed_bytes": bytes(payload), "error": None}

    raise AutoFirmaError(f"Tipo de payload no soportado: {type(payload).__name__}")


def extract_signature_metadata(signed_bytes: bytes, fmt: SignatureFormat) -> dict[str, Any]:
    """Extrae metadata del documento firmado (best-effort, sin libs externas).

    Devuelve {signer_nif, signer_cn, issuer_cn, has_signature}. Si una lib
    como `pyhanko` o `signxml` está disponible, podríamos extraer más,
    pero aquí nos limitamos a:

      - PAdES: buscar marca `/Type /Sig` en el PDF.
      - XAdES: buscar `<ds:Signature>` en el XML.

    El NIF/CN reales se rellenan cuando se integre una librería de parsing
    de certificados X.509 (pyOpenSSL/cryptography). Por ahora detectamos
    presencia de firma para que el `status` pase a "signed".
    """
    metadata: dict[str, Any] = {
        "signer_nif": None,
        "signer_cn": None,
        "issuer_cn": None,
        "has_signature": False,
    }

    if not signed_bytes:
        return metadata

    if fmt == SignatureFormat.PADES:
        # Buscar marker de firma PDF
        metadata["has_signature"] = b"/Type /Sig" in signed_bytes or b"/Type/Sig" in signed_bytes
    elif fmt == SignatureFormat.XADES:
        try:
            text = signed_bytes.decode("utf-8", errors="ignore")
            metadata["has_signature"] = "<ds:Signature" in text or "<Signature " in text or "<xades:" in text
        except Exception:
            metadata["has_signature"] = False
    elif fmt == SignatureFormat.CADES:
        # CAdES suele empezar con SEQUENCE ASN.1 (0x30) — heurística mínima
        metadata["has_signature"] = signed_bytes[:1] == b"\x30"

    return metadata
