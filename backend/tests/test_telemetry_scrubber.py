"""Tests para `telemetry_scrubber` (AI.SCR)."""

from app.core.telemetry_scrubber import (
    ALLOWED_FIELDS,
    hash_tenant_id,
    scrub_event,
    scrub_text,
)


class TestScrubText:
    def test_nif_se_redacta(self):
        assert scrub_text("Cliente 12345678A no encontrado") == "Cliente [REDACTED-NIF] no encontrado"

    def test_nie_se_redacta(self):
        assert scrub_text("DNI X1234567A") == "DNI [REDACTED-NIF]"

    def test_cif_se_redacta(self):
        assert scrub_text("Empresa B12345678") == "Empresa [REDACTED-NIF]"

    def test_iban_se_redacta(self):
        result = scrub_text("Transferencia a ES9121000418450200051332 OK")
        assert "[REDACTED-IBAN]" in result
        assert "ES91" not in result

    def test_iban_con_espacios(self):
        result = scrub_text("IBAN: ES91 2100 0418 4502 0005 1332")
        assert "[REDACTED-IBAN]" in result

    def test_email_se_redacta(self):
        result = scrub_text("Enviar a juan@empresa.es y a contacto@otra.com")
        assert result == "Enviar a [REDACTED-EMAIL] y a [REDACTED-EMAIL]"

    def test_tarjeta_se_redacta(self):
        result = scrub_text("Tarjeta 4532 1488 0343 6467")
        assert "[REDACTED-CARD]" in result
        assert "4532" not in result

    def test_ip_se_redacta(self):
        result = scrub_text("Conexión desde 192.168.1.100")
        assert result == "Conexión desde [REDACTED-IP]"

    def test_path_windows_se_normaliza(self):
        result = scrub_text(r"Error en C:\Users\Marcos\Desktop\app\file.py")
        assert "Marcos" not in result
        assert "<APP>" in result

    def test_path_posix_se_normaliza(self):
        result = scrub_text("Error en /home/marcos/app/file.py")
        assert "marcos" not in result
        assert "<APP>" in result

    def test_texto_limpio_no_cambia(self):
        assert scrub_text("Error genérico de conexión") == "Error genérico de conexión"

    def test_input_none_devuelve_none(self):
        assert scrub_text(None) is None

    def test_string_vacio(self):
        assert scrub_text("") == ""

    def test_combinacion_multiple_redactores(self):
        text = "Cliente 12345678A (juan@x.es) IBAN ES9121000418450200051332 IP 1.2.3.4"
        result = scrub_text(text)
        assert "[REDACTED-NIF]" in result
        assert "[REDACTED-EMAIL]" in result
        assert "[REDACTED-IBAN]" in result
        assert "[REDACTED-IP]" in result


class TestHashTenantId:
    def test_determinista_con_misma_sal(self):
        a = hash_tenant_id("tenant-abc-123", salt="sal-1")
        b = hash_tenant_id("tenant-abc-123", salt="sal-1")
        assert a == b

    def test_sal_diferente_produce_hash_diferente(self):
        # Salt por incidente rotada — la AEPD no puede correlacionar.
        a = hash_tenant_id("tenant-abc-123", salt="sal-1")
        b = hash_tenant_id("tenant-abc-123", salt="sal-2")
        assert a != b

    def test_longitud_16_chars(self):
        h = hash_tenant_id("tenant-1", salt="x")
        assert len(h) == 16


class TestScrubEvent:
    def test_solo_campos_whitelisted_pasan(self):
        event = {
            "tenant_id_hash": "abc123",
            "app_version": "1.0.0",
            "internal_id": "secret-12345",  # NO whitelisted
            "ip_address": "192.168.1.1",  # NO whitelisted
        }
        result = scrub_event(event)
        assert "tenant_id_hash" in result
        assert "app_version" in result
        assert "internal_id" not in result
        assert "ip_address" not in result

    def test_error_message_truncado_y_redactado(self):
        long_msg = (
            "Cliente 12345678A reportó problema con IBAN ES9121000418450200051332. " * 5
        )
        event = {"error_class": "ValueError", "error_message": long_msg}
        result = scrub_event(event)
        # Truncado a 200 chars (más o menos, +/- por reemplazos)
        assert len(result["error_message"]) < len(long_msg)
        # NIF e IBAN redactados
        assert "12345678A" not in result["error_message"]
        assert "ES9121" not in result["error_message"]

    def test_stack_trace_scrubbed(self):
        stack = "File 'C:\\Users\\Marcos\\Desktop\\app\\billing.py', line 123, in process_invoice"
        event = {"stack_trace": stack, "error_class": "KeyError"}
        result = scrub_event(event)
        assert "Marcos" not in result["stack_trace"]
        assert "<APP>" in result["stack_trace"]

    def test_campos_whitelist_completa(self):
        # Verificar que la whitelist incluye lo esperado del consenso Ronda 8 A.6
        expected = {
            "tenant_id_hash", "app_version", "os_family", "python_version",
            "error_class", "error_message", "stack_trace", "tool_name", "model_used",
        }
        assert expected.issubset(ALLOWED_FIELDS)

    def test_evento_vacio_devuelve_dict_vacio(self):
        assert scrub_event({}) == {}

    def test_no_se_filtran_campos_no_string_whitelisted(self):
        event = {"app_version": "1.0.0", "level": "error", "timestamp": "2026-05-14T12:00:00Z"}
        result = scrub_event(event)
        assert result["app_version"] == "1.0.0"
        assert result["level"] == "error"
        assert result["timestamp"] == "2026-05-14T12:00:00Z"
