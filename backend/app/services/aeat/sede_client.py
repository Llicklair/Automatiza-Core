"""Cliente HTTP para presentar modelos a la SEDE AEAT.

NOTA: Cada modelo de la AEAT tiene su propio endpoint, esquema XML y
namespaces. Mantener este catálogo actualizado por año fiscal es trabajo
continuo y crítico. Aquí solo declaramos las URLs base de pre/producción
para los modelos prioritarios; el envío real requiere validar el XSD
oficial publicado en la SEDE.

Hasta tener un certificado real y entorno de pruebas, devolvemos un
resultado en modo `dry_run` que no hace POST y simula una respuesta
exitosa con CSV ficticio. Esto permite iterar el flujo UI/UX/auditoría
sin riesgo.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

_log = logging.getLogger(__name__)


# Endpoints SOAP de la SEDE (REVISAR ANUALMENTE — pueden cambiar por orden ministerial)
SEDE_ENDPOINTS: dict[str, dict[str, str]] = {
    "303": {
        "preproduccion": "https://www7.aeat.es/wlpl/PRE-303/ws",
        "produccion": "https://www1.agenciatributaria.gob.es/wlpl/PRE-303/ws",
    },
    "130": {
        "preproduccion": "https://www7.aeat.es/wlpl/SDA-PCDR/ws",
        "produccion": "https://www1.agenciatributaria.gob.es/wlpl/SDA-PCDR/ws",
    },
    "111": {
        "preproduccion": "https://www7.aeat.es/wlpl/SDA-PCDR/ws",
        "produccion": "https://www1.agenciatributaria.gob.es/wlpl/SDA-PCDR/ws",
    },
}


@dataclass
class SubmissionResult:
    accepted: bool
    csv: str | None
    response_body: str
    error_code: str | None = None
    error_message: str | None = None
    dry_run: bool = False


class SedeError(RuntimeError):
    pass


def _endpoint_for(model_code: str, environment: str) -> str:
    catalog = SEDE_ENDPOINTS.get(model_code)
    if catalog is None:
        raise SedeError(f"Modelo {model_code} no soportado por este cliente todavía.")
    url = catalog.get(environment)
    if url is None:
        raise SedeError(f"Entorno '{environment}' no válido para modelo {model_code}.")
    return url


def _parse_response(body: str) -> SubmissionResult:
    """Parsea respuesta SOAP/XML de la SEDE. Captura CSV o código de error."""
    # CSV típico: 16 caracteres alfanuméricos en una etiqueta CSV o csvJustificante
    csv_match = re.search(r"<(?:csv|CSV|csvJustificante)>\s*([A-Z0-9]{16,20})\s*</", body)
    if csv_match:
        return SubmissionResult(
            accepted=True,
            csv=csv_match.group(1),
            response_body=body[:4000],
        )

    err_code = None
    err_msg = None
    code_match = re.search(r"<(?:codigoError|errorCode|Codigo)>\s*([\w\-]+)\s*</", body)
    msg_match = re.search(r"<(?:descripcionError|errorMessage|Descripcion|faultstring)>\s*(.+?)\s*</", body, re.DOTALL)
    if code_match:
        err_code = code_match.group(1)[:40]
    if msg_match:
        err_msg = msg_match.group(1).strip()[:1000]

    return SubmissionResult(
        accepted=False,
        csv=None,
        response_body=body[:4000],
        error_code=err_code,
        error_message=err_msg or "Sin descripción de error en la respuesta.",
    )


async def submit_signed_xml(
    model_code: str,
    signed_xml: str,
    environment: str = "preproduccion",
    dry_run: bool = True,
) -> SubmissionResult:
    """Envía el XML firmado a la SEDE AEAT.

    Cuando `dry_run=True` NO se hace POST: se devuelve una respuesta simulada
    con CSV ficticio para iterar el flujo. Cuando `dry_run=False` se hace
    POST real al endpoint correspondiente.
    """
    endpoint = _endpoint_for(model_code, environment)

    if dry_run:
        fake_csv = uuid4().hex[:16].upper()
        body = (
            f"<respuesta><resultado>OK</resultado>"
            f"<csv>{fake_csv}</csv>"
            f"<fecha>{datetime.utcnow().isoformat()}Z</fecha>"
            f"<dryRun>true</dryRun></respuesta>"
        )
        _log.info("AEAT dry-run submission: model=%s env=%s csv=%s", model_code, environment, fake_csv)
        return SubmissionResult(accepted=True, csv=fake_csv, response_body=body, dry_run=True)

    # Camino real: POST con cliente HTTP del certificado del cliente
    # (mTLS al WS de AEAT usa el mismo certificado para autenticación + firma del XML).
    try:
        import httpx  # ya es dependencia
    except ImportError as e:
        raise SedeError("httpx no instalado") from e

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "",
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(endpoint, content=signed_xml, headers=headers)
    except httpx.HTTPError as e:
        raise SedeError(f"Error HTTP al enviar a la SEDE: {e}") from e

    if r.status_code >= 500:
        return SubmissionResult(
            accepted=False, csv=None, response_body=r.text[:4000],
            error_code=f"HTTP_{r.status_code}",
            error_message=f"SEDE devolvió error de servidor ({r.status_code}).",
        )
    return _parse_response(r.text)
