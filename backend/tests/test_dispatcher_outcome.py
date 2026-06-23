"""Tests del detector estructurado de fallo de dispatchers (_outcome.detect_failure).

Cubre la señal principal: intent de ACCIÓN sin herramienta invocada → fallo
(el caso en que el LLM se rehúsa a usar tools y devuelve prosa convincente, que
antes se marcaba success=True).
"""
from app.agents.orchestrator.dispatchers._outcome import (
    detect_failure,
    tool_was_invoked,
    write_tool_was_invoked,
)


class _AIMsg:
    """Mensaje mínimo compatible con la inspección de tool_calls."""

    def __init__(self, content="", tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


def _msgs(tool: bool):
    msgs = [_AIMsg("intent del usuario")]
    if tool:
        msgs.append(_AIMsg("", tool_calls=[{"name": "create_invoice", "args": {}}]))
    msgs.append(_AIMsg("respuesta final"))
    return msgs


def test_empty_text_is_failure():
    assert detect_failure([], "", "crea factura")[0] is True


def test_error_prefix_is_failure():
    assert detect_failure(_msgs(tool=True), "Error: cliente inválido", "lista facturas")[0] is True


def test_fail_phrase_is_failure():
    assert detect_failure(_msgs(tool=True), "No se pudo crear la factura.", "crea factura")[0] is True


def test_tool_refusal_is_failure():
    is_err, _ = detect_failure(
        _msgs(tool=False), "Las herramientas del CRM no están disponibles.", "lista clientes"
    )
    assert is_err is True


def test_action_intent_without_tool_is_failure():
    """El caso clave: prosa convincente pero ninguna tool invocada."""
    is_err, reason = detect_failure(
        _msgs(tool=False), "He creado la factura correctamente.", "crea una factura para ACME"
    )
    assert is_err is True
    assert "no invocó" in (reason or "")


def test_action_intent_with_tool_is_success():
    assert detect_failure(_msgs(tool=True), "Factura creada.", "crea una factura para ACME")[0] is False


def test_query_intent_without_tool_is_success():
    # "lista" no es verbo de acción → no se exige tool; respuesta válida.
    assert detect_failure(_msgs(tool=False), "Tienes 3 facturas pendientes.", "lista las facturas")[0] is False


def test_not_found_is_query_ok_but_action_fails():
    assert detect_failure(_msgs(tool=True), "No se encontró el cliente.", "busca cliente", strict_not_found=False)[0] is False
    assert detect_failure(_msgs(tool=True), "No se encontró el cliente.", "actualiza el cliente", strict_not_found=True)[0] is True


def test_normal_success():
    assert detect_failure(_msgs(tool=True), "He creado la factura F-001.", "crea factura")[0] is False


def test_tool_was_invoked():
    assert tool_was_invoked(_msgs(tool=True)) is True
    assert tool_was_invoked(_msgs(tool=False)) is False
    assert tool_was_invoked([]) is False
    assert tool_was_invoked(None) is False


# --- Regresión auditoría E2E 2026-06-23: phantom-write + verbos/frases nuevos ---


def _msgs_tool(name: str):
    """Mensajes con UNA tool invocada de nombre arbitrario (para distinguir read/write)."""
    return [_AIMsg("intent"), _AIMsg("", tool_calls=[{"name": name, "args": {}}]), _AIMsg("final")]


def test_phantom_write_only_read_tool_is_failure():
    # Acción pedida pero solo se invocó una tool de LECTURA → la operación no se ejecutó.
    # Antes (regla "0 tools") esto pasaba como success=True (phantom-write).
    is_err, _ = detect_failure(
        _msgs_tool("get_product_catalog"), "He preparado la campana.", "crea una campana"
    )
    assert is_err is True


def test_action_with_write_tool_is_success():
    assert detect_failure(_msgs_tool("create_campaign"), "Campana creada.", "crea una campana")[0] is False


def test_abrir_verb_without_tool_is_failure():
    assert detect_failure([], "He abierto el puesto.", "abre un puesto de trabajo")[0] is True


def test_no_dispongo_de_refusal_is_failure():
    is_err, _ = detect_failure(
        [_AIMsg("No dispongo de herramientas de RRHH.")],
        "No dispongo de herramientas de RRHH.",
        "abre un puesto",
    )
    assert is_err is True


def test_write_tool_was_invoked_excludes_reads():
    assert write_tool_was_invoked(_msgs_tool("create_invoice")) is True
    assert write_tool_was_invoked(_msgs_tool("update_stock")) is True
    assert write_tool_was_invoked(_msgs_tool("list_payrolls")) is False
    assert write_tool_was_invoked(_msgs_tool("get_account_balance")) is False
