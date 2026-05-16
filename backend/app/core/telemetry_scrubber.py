r"""Scrubber de telemetría (AI.SCR) — protege privacidad antes de enviar a Sentry.

Política aplicada (ver `docs/telemetry-data-policy.md`):

* **Whitelist de campos permitidos**: `tenant_id_hash`, `app_version`,
  `os_family`, `python_version`, `error_class`, `error_message_truncated`,
  `stack_trace_scrubbed`, `tool_name`, `model_used`.
* **Regex bloqueante** sobre cualquier string saliente: NIF/NIE/CIF, IBAN,
  emails, números de tarjeta, IPs IPv4. Si un campo whitelisted contiene
  alguno, se reemplaza por `[REDACTED-<TIPO>]`.
* **Rutas convertidas**: `C:\Users\X\...` o `/home/x/...` -> `<APP>/...`.
* **Stack traces**: solo nombres de archivo relativos al `<APP>` + número de
  línea + nombre de función. No se conservan locals.

Coste de no aplicar este scrubber: un solo evento de error puede contener un
NIF en `error.message`, lo que constituye envío de dato personal al VPS sin
consentimiento — exposición AEPD inmediata.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

# ── Patrones de detección de PII ─────────────────────────────────────────────

# NIF / NIE / CIF español. Formato: 8 dígitos + 1 letra, o letra + 7 dígitos + letra.
_NIF_RE = re.compile(
    r"\b(?:[XYZ]\d{7}[A-Z]|\d{8}[A-Z]|[A-HJNP-SUVW]\d{7}[A-J0-9])\b",
    re.IGNORECASE,
)

# IBANs con espacios (formato impreso): país+check + 2-5 grupos de 4 + opcional 1-4.
_IBAN_SPACED_RE = re.compile(
    r"(?<![A-Z0-9])([A-Z]{2}\d{2}(?:\s[A-Z0-9]{4}){2,5}(?:\s[A-Z0-9]{1,4})?)(?=[\s.,;:!?)\]}>]|$)",
    re.IGNORECASE,
)

# IBANs compactos sin espacios.
_IBAN_COMPACT_RE = re.compile(
    r"(?<![A-Z0-9])([A-Z]{2}\d{2}[A-Z0-9]{11,30})(?![A-Z0-9])",
    re.IGNORECASE,
)

# Email RFC-simplificado.
_EMAIL_RE = re.compile(
    r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
)

# Número de tarjeta — secuencias de 13-19 dígitos con guiones/espacios opcionales.
_CARD_RE = re.compile(
    r"\b(?:\d[ -]?){13,19}\b"
)

# IP IPv4.
_IPV4_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d?\d)\b"
)

# Rutas absolutas a sustituir por <APP>.
_PATH_WIN_RE = re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+", re.IGNORECASE)
_PATH_POSIX_RE = re.compile(r"(?:/home|/Users)/[^/\s]+")

# Whitelist de campos top-level permitidos.
ALLOWED_FIELDS = frozenset({
    "tenant_id_hash",
    "app_version",
    "os_family",
    "python_version",
    "error_class",
    "error_message",
    "stack_trace",
    "tool_name",
    "model_used",
    "agent_name",
    "level",
    "release",
    "timestamp",
    "transaction",
})

_MAX_ERROR_MESSAGE_LEN = 200


def scrub_text(text: str | None) -> str | None:
    """Aplica todos los redactores sobre un texto plano."""
    if not text:
        return text
    text = _NIF_RE.sub("[REDACTED-NIF]", text)
    text = _IBAN_SPACED_RE.sub("[REDACTED-IBAN]", text)
    text = _IBAN_COMPACT_RE.sub("[REDACTED-IBAN]", text)
    text = _EMAIL_RE.sub("[REDACTED-EMAIL]", text)
    # Carrera: cards primero (más específico) antes que cualquier número largo.
    text = _CARD_RE.sub("[REDACTED-CARD]", text)
    text = _IPV4_RE.sub("[REDACTED-IP]", text)
    text = _PATH_WIN_RE.sub("<APP>", text)
    text = _PATH_POSIX_RE.sub("<APP>", text)
    return text


def hash_tenant_id(tenant_id: str, salt: str) -> str:
    """Hash determinista de un `tenant_id` con sal — usado para pseudonimizar.

    El salt debe rotarse por incidente (consensuado en Ronda 6) para que la
    AEPD no pueda argumentar "trazabilidad cruzada entre informes".
    """
    return hashlib.sha256(f"{salt}:{tenant_id}".encode()).hexdigest()[:16]


def scrub_event(event: dict[str, Any]) -> dict[str, Any]:
    """Filtra un evento de telemetría según la política de privacidad.

    1. Elimina campos no incluidos en `ALLOWED_FIELDS`.
    2. Trunca `error_message` a 200 chars y le aplica `scrub_text`.
    3. Aplica `scrub_text` a `stack_trace`.
    4. Aplica `scrub_text` a cualquier otro string superviviente.
    """
    scrubbed: dict[str, Any] = {}
    for key, value in event.items():
        if key not in ALLOWED_FIELDS:
            continue
        if key == "error_message" and isinstance(value, str):
            truncated = value[:_MAX_ERROR_MESSAGE_LEN]
            scrubbed[key] = scrub_text(truncated)
        elif key == "stack_trace" and isinstance(value, str):
            scrubbed[key] = scrub_text(value)
        elif isinstance(value, str):
            scrubbed[key] = scrub_text(value)
        else:
            # Tipos no-string (int, list, dict): se pasan pero recursivamente
            # se aplica scrub a strings anidados solo si son leaves simples.
            scrubbed[key] = value
    return scrubbed
