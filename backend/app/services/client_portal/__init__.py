"""Portal de clientes — servicios de dominio.

Expone la emisión y verificación de tokens de acceso al portal externo.
La capa HTTP (`api/v1/routes/client_portal.py`) delega aquí toda la
lógica criptográfica y de persistencia.
"""

from app.services.client_portal.tokens import (
    hash_token,
    issue_token,
)

__all__ = ["hash_token", "issue_token"]
