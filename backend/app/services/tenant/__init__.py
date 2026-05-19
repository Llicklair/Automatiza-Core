"""Tenant — servicios de dominio.

Para la gestión genérica del tenant (CRUD, LLM config) ver
`app.services.tenant_service`. Aquí viven flujos específicos como
la instalación de certificados digitales.
"""

from app.services.tenant.certificates import (
    CertificateInfo,
    install_certificate,
)

__all__ = ["CertificateInfo", "install_certificate"]
