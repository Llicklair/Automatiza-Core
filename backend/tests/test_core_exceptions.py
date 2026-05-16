"""Tests para app.core.exceptions — Jerarquía de excepciones."""
import pytest
from app.core.exceptions import (
    AppException,
    ConflictError,
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)


class TestAppException:
    def test_default_message(self):
        exc = AppException()
        assert exc.detail == "Error interno del servidor"

    def test_custom_message(self):
        exc = AppException("algo salió mal")
        assert exc.detail == "algo salió mal"

    def test_status_code(self):
        assert AppException.status_code == 500

    def test_error_type(self):
        assert AppException.error_type == "internal_error"

    def test_is_exception(self):
        exc = AppException("err")
        assert isinstance(exc, Exception)

    def test_str_representation(self):
        exc = AppException("test msg")
        assert str(exc) == "test msg"


class TestNotFoundError:
    def test_default_message(self):
        exc = NotFoundError()
        assert exc.detail == "Recurso no encontrado"

    def test_custom_message(self):
        exc = NotFoundError("Cliente no encontrado")
        assert exc.detail == "Cliente no encontrado"

    def test_status_code(self):
        assert NotFoundError.status_code == 404

    def test_error_type(self):
        assert NotFoundError.error_type == "not_found"

    def test_inherits_app_exception(self):
        assert issubclass(NotFoundError, AppException)


class TestValidationError:
    def test_default_message(self):
        exc = ValidationError()
        assert exc.detail == "Datos de entrada invalidos"

    def test_custom_message(self):
        exc = ValidationError("NIF inválido")
        assert exc.detail == "NIF inválido"

    def test_status_code(self):
        assert ValidationError.status_code == 422

    def test_error_type(self):
        assert ValidationError.error_type == "validation_error"

    def test_inherits_app_exception(self):
        assert issubclass(ValidationError, AppException)


class TestConflictError:
    def test_default_message(self):
        exc = ConflictError()
        assert exc.detail == "El recurso ya existe o hay un conflicto"

    def test_status_code(self):
        assert ConflictError.status_code == 409

    def test_error_type(self):
        assert ConflictError.error_type == "conflict"


class TestForbiddenError:
    def test_default_message(self):
        exc = ForbiddenError()
        assert exc.detail == "No tienes permisos para esta accion"

    def test_status_code(self):
        assert ForbiddenError.status_code == 403

    def test_error_type(self):
        assert ForbiddenError.error_type == "forbidden"


class TestExternalServiceError:
    def test_default_message(self):
        exc = ExternalServiceError()
        assert exc.detail == "Error en servicio externo"

    def test_custom_message(self):
        exc = ExternalServiceError("Timeout en API de Stripe")
        assert exc.detail == "Timeout en API de Stripe"

    def test_status_code(self):
        assert ExternalServiceError.status_code == 502

    def test_error_type(self):
        assert ExternalServiceError.error_type == "external_service_error"

    def test_inherits_app_exception(self):
        assert issubclass(ExternalServiceError, AppException)


class TestExceptionHierarchy:
    @pytest.mark.parametrize(
        "exc_cls",
        [NotFoundError, ValidationError, ConflictError, ForbiddenError, ExternalServiceError],
    )
    def test_all_subclass_app_exception(self, exc_cls):
        assert issubclass(exc_cls, AppException)

    @pytest.mark.parametrize(
        "exc_cls",
        [NotFoundError, ValidationError, ConflictError, ForbiddenError, ExternalServiceError],
    )
    def test_all_are_catchable_as_exception(self, exc_cls):
        with pytest.raises(Exception):
            raise exc_cls()
