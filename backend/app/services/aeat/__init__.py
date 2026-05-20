"""Servicios AEAT — generación de modelos fiscales en formatos oficiales.

Esta capa NO presenta a la SEDE AEAT (eso requiere certificado digital y
firma XAdES, ver Fase C del roadmap). Solo prepara el expediente para que
el usuario lo presente él mismo desde la SEDE con su propio certificado.
"""

from app.services.aeat.casillas_303 import (
    Casilla303,
    build_casillas_303,
)
from app.services.aeat.expediente_303 import (
    ExpedienteError,
    build_expediente_303,
)
from app.services.aeat.modelo_303_xml import build_modelo_303_xml

__all__ = [
    "Casilla303",
    "build_casillas_303",
    "build_modelo_303_xml",
    "build_expediente_303",
    "ExpedienteError",
]
