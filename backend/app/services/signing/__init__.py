"""Firma electrónica eIDAS con AutoFirma del Estado (F3.11).

Flujo:

  1. Cliente sube documento → backend genera session_token y URI `afirma://`.
  2. Frontend redirige a la URI → AutoFirma se abre con el certificado FNMT
     del usuario instalado en el equipo, firma el documento.
  3. AutoFirma POSTea el documento firmado al callback con el session_token.
  4. Backend verifica firma, extrae metadata del firmante y persiste.

API pública:
  - `start_signing_session(...)`        → URI afirma:// + session_token.
  - `process_signed_callback(...)`      → procesa firmado entrante.
  - `build_autofirma_uri(...)`          → builder puro (testeable sin DB).
  - `extract_signature_metadata(...)`   → parser PAdES/XAdES (best-effort).
"""

from app.services.signing.autofirma import (
    AutoFirmaError,
    SignatureFormat,
    build_autofirma_uri,
    extract_signature_metadata,
    parse_autofirma_response,
)
from app.services.signing.sessions import (
    get_signing_status,
    process_signed_callback,
    start_signing_session,
)

__all__ = [
    "AutoFirmaError",
    "SignatureFormat",
    "build_autofirma_uri",
    "extract_signature_metadata",
    "parse_autofirma_response",
    "get_signing_status",
    "process_signed_callback",
    "start_signing_session",
]
