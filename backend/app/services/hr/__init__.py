"""HR domain services — re-exports for backwards compatibility."""

from app.services.hr import documents, recruitment, service

__all__ = ["service", "documents", "recruitment"]
