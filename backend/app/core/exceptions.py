"""Jerarquia de excepciones tipadas para respuestas estructuradas."""

from __future__ import annotations


class AppException(Exception):
    """Base para excepciones de la aplicacion."""

    status_code: int = 500
    error_type: str = "internal_error"

    def __init__(self, detail: str = "Error interno del servidor"):
        self.detail = detail
        super().__init__(detail)


class NotFoundError(AppException):
    status_code = 404
    error_type = "not_found"

    def __init__(self, detail: str = "Recurso no encontrado"):
        super().__init__(detail)


class ValidationError(AppException):
    status_code = 422
    error_type = "validation_error"

    def __init__(self, detail: str = "Datos de entrada invalidos"):
        super().__init__(detail)


class ConflictError(AppException):
    status_code = 409
    error_type = "conflict"

    def __init__(self, detail: str = "El recurso ya existe o hay un conflicto"):
        super().__init__(detail)


class ForbiddenError(AppException):
    status_code = 403
    error_type = "forbidden"

    def __init__(self, detail: str = "No tienes permisos para esta accion"):
        super().__init__(detail)


class ExternalServiceError(AppException):
    status_code = 502
    error_type = "external_service_error"

    def __init__(self, detail: str = "Error en servicio externo"):
        super().__init__(detail)


class OrchestratorTimeoutError(AppException):
    """Timeout del orquestador LangGraph (cuelgue del LLM interno, no de red).

    Hereda de AppException (NO de TimeoutError de stdlib) intencionalmente:
    el TaskRunner usa isinstance(exc, TimeoutError) como señal de error
    transient (retry). Un cuelgue del LLM interno NO es transient — repetir
    la misma instrucción produce el mismo cuelgue. Marcar como no-retry
    para que la task pase a `failed` en segundos en vez de en ~15 min tras
    3 reintentos.
    """

    status_code = 504
    error_type = "orchestrator_timeout"

    def __init__(self, detail: str = "El orquestador excedió el tiempo límite"):
        super().__init__(detail)
