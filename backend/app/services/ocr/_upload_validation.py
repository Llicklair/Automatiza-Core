"""Validación de entrada para los endpoints OCR (escaneo de tickets/facturas).

Rechaza ficheros con extensión no soportada ANTES de invocar el LLM, evitando
gastar tokens (y exponer el scanner) con `.exe`, `.txt`, `.zip`, etc.

El allowlist se deriva del `SUPPORTED_MIME` de cada scanner (única fuente de
verdad) para que ambos no se desincronicen. No se reutiliza el `validate_upload`
de `services/documents` a propósito: su allowlist es de gestión documental
(incluye `.docx`, `.xlsx`, `.zip`, `.eml`…) y aceptaría ficheros que el OCR
rechaza luego con un 415 menos claro.
"""

import os

from fastapi import HTTPException, UploadFile, status

from app.services.ocr.invoice_scanner import SUPPORTED_MIME as INVOICE_MIME
from app.services.ocr.receipt_scanner import SUPPORTED_MIME as RECEIPT_MIME

# MIME → extensiones equivalentes. Solo cubre los tipos soportados por el OCR.
_MIME_EXTENSIONS: dict[str, set[str]] = {
    "image/png": {".png"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/webp": {".webp"},
    "image/gif": {".gif"},
    "application/pdf": {".pdf"},
}


def _extensions_for(supported_mime: set[str]) -> set[str]:
    exts: set[str] = set()
    for mime in supported_mime:
        exts |= _MIME_EXTENSIONS.get(mime, set())
    return exts


RECEIPT_EXTENSIONS = _extensions_for(RECEIPT_MIME)  # {.png, .jpg, .jpeg, .webp, .gif}
INVOICE_EXTENSIONS = _extensions_for(INVOICE_MIME)  # + .pdf


def validate_ocr_upload(file: UploadFile, allowed_extensions: set[str]) -> None:
    """Valida un UploadFile contra el allowlist OCR. Lanza HTTPException(415) si falla.

    Se valida por EXTENSIÓN del nombre (determinista, no depende del content_type
    que el cliente puede falsear). No lee el cuerpo del fichero.
    """
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Formato '{ext or '(sin extensión)'}' no soportado. Usa: {allowed}.",
        )
