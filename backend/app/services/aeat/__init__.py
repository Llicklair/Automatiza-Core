"""Servicios AEAT — generación + presentación electrónica de modelos fiscales.

Capas:
  - casillas_303 / modelo_303_xml / expediente_303 — Fase A: preparar el
    expediente para presentación manual en SEDE (PDF + XML auxiliar).
  - certificate_storage — custodia cifrada del .pfx del cliente (Fase C).
  - xades_signer — firma XAdES-BES (Fase C, requiere xmlsec/signxml).
  - sede_client — cliente HTTP a SEDE AEAT (Fase C, soporta dry-run).
  - presentation_service — orquestador del flujo de presentación (Fase C).
"""

from app.services.aeat.casillas_303 import (
    Casilla303,
    build_casillas_303,
)
from app.services.aeat.certificate_storage import (
    CertificateError,
    cert_to_dict,
    get_active_certificate,
    load_decrypted,
    revoke_certificate,
    store_certificate,
)
from app.services.aeat.expediente_303 import (
    ExpedienteError,
    build_expediente_303,
)
from app.services.aeat.modelo_303_xml import build_modelo_303_xml
from app.services.aeat.modelo_xml_generico import build_modelo_xml_generic
from app.services.aeat.presentation_service import (
    build_acuse_text,
    get_presentation,
    PresentationError,
    create_presentation,
    list_presentations,
    presentation_to_dict,
    submit_presentation,
)
from app.services.aeat.sede_client import SedeError
from app.services.aeat.xades_signer import SigningError

__all__ = [
    # Modelo 303 (Fase A)
    "Casilla303",
    "build_casillas_303",
    "build_modelo_303_xml",
    "build_modelo_xml_generic",
    "build_expediente_303",
    "ExpedienteError",
    # Certificado (Fase C)
    "CertificateError",
    "store_certificate",
    "get_active_certificate",
    "load_decrypted",
    "revoke_certificate",
    "cert_to_dict",
    # Presentación (Fase C)
    "PresentationError",
    "build_acuse_text",
    "get_presentation",
    "create_presentation",
    "submit_presentation",
    "list_presentations",
    "presentation_to_dict",
    # Errores propagados
    "SedeError",
    "SigningError",
]
