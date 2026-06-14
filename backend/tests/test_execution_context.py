"""Tests para app.services.execution_context.

Cubre:
    (a) extracción estructurada existente (key_data desde _EXTRACTABLE_KEYS)
    (b) fallback a response_preview con cap mayor (~1k tokens / 4000 chars)
    (c) parser regex extrae nombre de factura / cliente / UUID desde markdown
"""

from app.services import execution_context as ec
from app.services.execution_context import (
    ExecutionContext,
    _parse_markdown_entities,
    _truncate_response_text,
)


def _state_with_result(output: dict, agent: str = "billing", success: bool = True) -> dict:
    return {
        "tenant_id": "t1",
        "task_id": "task1",
        "user_id": "u1",
        "user_intent": "intent original",
        "agent_results": [
            {"agent": agent, "output": output, "success": success}
        ],
    }


# ──────────────────────────────────────────────────────────────────────────────
# (a) Extracción estructurada existente — no se rompe el flujo previo
# ──────────────────────────────────────────────────────────────────────────────


def test_extracts_structured_keys_into_entities_and_keydata():
    output = {
        "action": "draft_created",
        "invoice_id": "inv-abc",
        "invoice_number": "IA-2026-0001",
        "client_name": "Acme SL",
        "amount_total": 1815.0,
    }
    ctx = ExecutionContext.from_state(_state_with_result(output))

    # Entidades canónicas extraídas
    assert ctx.entities["invoice_id"] == "inv-abc"
    assert ctx.entities["invoice_number"] == "IA-2026-0001"
    assert ctx.entities["client_name"] == "Acme SL"
    assert ctx.entities["amount_total"] == 1815.0

    # key_data del único step contiene esas claves
    step = ctx.step_summaries[0]
    assert step["agent"] == "billing"
    assert step["key_data"]["invoice_id"] == "inv-abc"
    assert step["key_data"]["client_name"] == "Acme SL"
    assert step["success"] is True


def test_extracts_from_nested_extracted_data():
    """billing devuelve `extracted_data` con las claves; deben subir a entities."""
    output = {
        "action": "draft_created",
        "extracted_data": {"client_nif": "B12345678", "vat_rate": 21},
    }
    ctx = ExecutionContext.from_state(_state_with_result(output))
    assert ctx.entities["client_nif"] == "B12345678"
    assert ctx.entities["vat_rate"] == 21


# ──────────────────────────────────────────────────────────────────────────────
# (b) Fallback de response_preview con cap mayor
# ──────────────────────────────────────────────────────────────────────────────


def test_response_preview_uses_larger_cap_than_400():
    """Antes el cap era 400 chars; ahora debe ser ≥ 400 (idealmente ~4000)."""
    long_response = "x" * 2000  # 2000 chars, por debajo del cap 4000
    output = {"action": "completed", "response": long_response}
    ctx = ExecutionContext.from_state(_state_with_result(output, agent="rag"))

    preview = ctx.step_summaries[0]["response_preview"]
    assert preview is not None
    # No debe truncarse a 400: el texto entero (o casi) entra.
    assert len(preview) >= 1000, f"preview demasiado corto: {len(preview)}"
    # No añade '…' si entró completo
    assert preview.startswith("xxxx")


def test_response_preview_truncates_beyond_cap():
    """Por encima del cap (~4000 chars o 1k tokens) se trunca con '…'."""
    huge = "y" * 20000  # claramente por encima de cualquier cap razonable
    output = {"action": "completed", "response": huge}
    ctx = ExecutionContext.from_state(_state_with_result(output, agent="rag"))

    preview = ctx.step_summaries[0]["response_preview"]
    assert preview is not None
    assert preview.endswith("…")
    # Cap defensivo: nunca devolver el texto íntegro
    assert len(preview) < len(huge)


def test_truncate_helper_short_text_unchanged():
    assert _truncate_response_text("hola") == "hola"


def test_build_enriched_intent_includes_response_when_no_keydata():
    output = {"action": "completed", "response": "Resumen: tres facturas pendientes"}
    ctx = ExecutionContext.from_state(_state_with_result(output, agent="rag"))

    enriched = ctx.build_enriched_intent("siguiente paso")
    assert "siguiente paso" in enriched
    assert "Paso 1 (rag): completed" in enriched
    assert "Resumen: tres facturas pendientes" in enriched


# ──────────────────────────────────────────────────────────────────────────────
# (c) Parser regex extrae claves obvias del markdown
# ──────────────────────────────────────────────────────────────────────────────


def test_markdown_parser_extracts_invoice_and_client():
    md = (
        "Factura creada con éxito.\n"
        "Factura: IA-2026-0001\n"
        "Cliente: Acme SL\n"
        "NIF: B12345678\n"
    )
    out = _parse_markdown_entities(md)
    assert out["invoice_number"] == "IA-2026-0001"
    assert out["client_name"] == "Acme SL"
    assert out["client_nif"] == "B12345678"


def test_markdown_parser_handles_bold():
    md = "**Factura:** IA-2026-0007\n**Cliente:** Globex"
    out = _parse_markdown_entities(md)
    assert out["invoice_number"] == "IA-2026-0007"
    assert out["client_name"] == "Globex"


def test_markdown_parser_extracts_uuid_as_document_id():
    md = "Documento subido correctamente con id 550e8400-e29b-41d4-a716-446655440000"
    out = _parse_markdown_entities(md)
    assert out["document_id"] == "550e8400-e29b-41d4-a716-446655440000"


def test_markdown_parser_empty_text_returns_empty():
    assert _parse_markdown_entities("") == {}
    assert _parse_markdown_entities("texto sin pares clave valor") == {}


def test_markdown_parser_does_not_override_structured_entities():
    """Si el output ya trae invoice_number estructurado, el parser markdown
    NO debe pisarlo, aunque el response también lo mencione con otro valor."""
    output = {
        "action": "draft_created",
        "invoice_number": "IA-OFICIAL",
        "response": "Factura: IA-FANTASMA\nCliente: Acme SL",
    }
    ctx = ExecutionContext.from_state(_state_with_result(output, agent="billing"))
    # Gana el estructurado
    assert ctx.entities["invoice_number"] == "IA-OFICIAL"
    # Pero el parser SÍ añade claves nuevas que el estructurado no tenía
    assert ctx.entities["client_name"] == "Acme SL"


def test_default_extractable_keys_unchanged():
    """Sanity check: el listado de claves canónicas no se ha alterado por error."""
    assert "invoice_id" in ec._EXTRACTABLE_KEYS
    assert "client_name" in ec._EXTRACTABLE_KEYS
    assert "employee_name" in ec._EXTRACTABLE_KEYS


# ──────────────────────────────────────────────────────────────────────────────
# (d) El preview del ÚLTIMO paso se incluye aunque tenga key_data (no perder
#     datos que la extracción estructurada no capturó)
# ──────────────────────────────────────────────────────────────────────────────


def _multi_state(results: list[dict]) -> dict:
    return {
        "tenant_id": "t1",
        "task_id": "task1",
        "user_id": "u1",
        "user_intent": "intent original",
        "agent_results": results,
    }


def test_last_step_preview_included_even_with_keydata():
    # billing creó la factura (key_data invoice_id) PERO la prosa lleva datos que
    # el paso siguiente (email) necesita y que no son claves canónicas.
    output = {
        "action": "draft_created",
        "invoice_id": "inv-abc",
        "response": "Factura creada. Email del cliente: pagos@acme.com. Importe: 1815 EUR.",
    }
    ctx = ExecutionContext.from_state(_state_with_result(output, agent="billing"))
    enriched = ctx.build_enriched_intent("envía la factura por email")

    assert "invoice_id: inv-abc" in enriched   # key_data estructurado presente
    assert "pagos@acme.com" in enriched        # y la prosa del último paso TAMBIÉN
    assert "respuesta:" in enriched


def test_older_step_prose_suppressed_but_last_step_shown():
    # Marcadores en prosa SIN patrón "Etiqueta: valor" ni IDs con guion, para no
    # disparar el parser de markdown (que extraería entidades) y aislar así lo que
    # este test verifica: la (no)inclusión del response_preview.
    step1 = {
        "agent": "billing",
        "success": True,
        "output": {
            "action": "draft_created",
            "invoice_id": "inv1",
            "response": "Primer paso completado sin novedad MARCADORVIEJO aqui.",
        },
    }
    step2 = {
        "agent": "crm",
        "success": True,
        "output": {
            "action": "completed",
            "opportunity_id": "opp9",
            "response": "Segundo paso completado MARCADORNUEVO aqui.",
        },
    }
    ctx = ExecutionContext.from_state(_multi_state([step1, step2]))
    enriched = ctx.build_enriched_intent("siguiente paso")

    # El último paso (crm) muestra su prosa aunque tenga key_data.
    assert "MARCADORNUEVO" in enriched
    # El paso ANTERIOR (billing) con key_data NO incluye su prosa (solo key_data),
    # para no inflar el prompt con prosa de pasos lejanos.
    assert "MARCADORVIEJO" not in enriched
    assert "invoice_id: inv1" in enriched
    assert "opportunity_id: opp9" in enriched


def test_logs_when_step_yields_no_structured_entities(caplog):
    import logging

    output = {"action": "completed", "response": "Texto en prosa sin etiquetas reconocibles."}
    with caplog.at_level(logging.DEBUG, logger="app.services.execution_context"):
        ExecutionContext.from_state(_state_with_result(output, agent="rag"))
    assert "no aportó entidades" in caplog.text


# ──────────────────────────────────────────────────────────────────────────────
# (e) El parser NO trata el guion de un ID como separador ni se traga la frase
# ──────────────────────────────────────────────────────────────────────────────


def test_markdown_parser_ignores_inline_hyphen_id():
    # "Factura IA-001" inline (sin "Etiqueta: valor") NO debe extraer una entidad
    # basura con la oración siguiente como valor.
    out = _parse_markdown_entities("Factura IA-001. Texto adicional aquí.")
    assert out.get("invoice_number") != "001. Texto adicional aquí"
    assert "invoice_number" not in out


def test_markdown_parser_value_stops_at_sentence_boundary():
    out = _parse_markdown_entities("Cliente: Acme SL. Detalles irrelevantes que no son el valor.")
    assert out["client_name"] == "Acme SL"


def test_markdown_parser_preserves_decimals_in_value():
    # El corte por ". " no debe romper decimales ("1815.00") porque el punto NO
    # va seguido de espacio.
    out = _parse_markdown_entities("Concepto: Servicios 1815.00 EUR")
    assert out["concept"] == "Servicios 1815.00 EUR"
