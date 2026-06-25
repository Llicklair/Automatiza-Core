import re
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# IBANs con espacios (formato impreso "ES91 2100 0418 4502 0005 1332"):
# país+check seguido de 2-5 grupos de 4 alfanuméricos + grupo opcional 1-4,
# terminado en espacio, puntuación o fin de string para evitar absorber palabras
# normales que casualmente tengan 4 letras consecutivas.
_IBAN_SPACED_RE = re.compile(
    r"(?<![A-Z0-9])([A-Z]{2}\d{2}(?:\s[A-Z0-9]{4}){2,5}(?:\s[A-Z0-9]{1,4})?)(?=[\s.,;:!?)\]}>]|$)",
    re.IGNORECASE,
)

# IBANs compactos sin espacios.
_IBAN_COMPACT_RE = re.compile(
    r"(?<![A-Z0-9])([A-Z]{2}\d{2}[A-Z0-9]{11,30})(?![A-Z0-9])",
    re.IGNORECASE,
)


def mask_iban(value: str | None) -> str | None:
    """Enmascara IBANs en `value`, dejando visible solo el país y los 4 últimos dígitos.

    Detecta IBANs con o sin espacios internos. Idempotente: aplicar dos veces no
    re-enmascara lo ya enmascarado (los `*` no encajan en `[A-Z0-9]`).
    Devuelve el valor original si la longitud no corresponde a un IBAN válido.
    """
    if not value:
        return value

    def _build_masked(raw: str) -> str | None:
        full = raw.replace(" ", "").upper()
        if not 15 <= len(full) <= 34:
            return None
        country = full[:2]
        last4 = full[-4:]
        middle_groups = (len(full) - 6) // 4
        masked = " ".join(["****"] * middle_groups)
        return f"{country}** {masked} {last4}".strip()

    def _sub(match: re.Match[str]) -> str:
        masked = _build_masked(match.group(1))
        return masked if masked else match.group(0)

    value = _IBAN_SPACED_RE.sub(_sub, value)
    value = _IBAN_COMPACT_RE.sub(_sub, value)
    return value


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_client_portal_access_token(client_id: str, tenant_id: str) -> str:
    """JWT de sesión del portal de clientes (type=client_portal).

    TTL corto (24 h en vez de 7 días, M1): es una sesión derivada del magic-link
    `ClientPortalToken`; el cliente la renueva re-canjeando el enlace. Además
    `get_current_client_portal` exige que el ClientPortalToken siga activo, así que
    revocarlo en BD invalida los JWT ya emitidos.
    """
    expire = datetime.now(UTC) + timedelta(hours=24)
    payload = {"sub": client_id, "tenant_id": tenant_id, "exp": expire, "type": "client_portal"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
