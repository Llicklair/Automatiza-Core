"""Portal de clientes — servicios de dominio.

Expone la emisión y verificación de tokens de acceso al portal externo
y las consultas de negocio que usa la capa HTTP.
"""

from app.services.client_portal.queries import (
    PortalAuthError,
    authenticate_and_stamp,
    get_invoice_for_client,
    get_portal_me,
    get_portal_token_status,
    revoke_portal_tokens,
)
from app.services.client_portal.tokens import (
    hash_token,
    issue_token,
)

__all__ = [
    "hash_token",
    "issue_token",
    "PortalAuthError",
    "authenticate_and_stamp",
    "get_invoice_for_client",
    "get_portal_me",
    "get_portal_token_status",
    "revoke_portal_tokens",
]
