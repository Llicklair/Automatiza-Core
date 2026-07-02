"""Detección ESTRUCTURADA de fallo de un agente LangGraph.

Reemplaza el substring-matching frágil sobre la respuesta del LLM (que marcaba
`success=True` cuando el LLM se rehusaba a usar tools y devolvía prosa) por una
señal estructurada principal:

    intent de ACCIÓN (crea/actualiza/envía/calcula…) + 0 herramientas invocadas
    → la operación NO se ejecutó, aunque el texto sea convincente.

La detección de acción se hace sobre el INTENT del usuario (estable), no sobre la
respuesta del LLM (inestable) — ver lección 2026-05-08. Se complementa con una
lista curada de frases INEQUÍVOCAS de fallo y la detección de respuesta vacía.

Las frases ambiguas que dependen de si la operación es una consulta ("no existe",
"no encontrado") solo cuentan como fallo con `strict_not_found=True` — lo activan
los dispatchers que distinguen query de acción (billing) cuando NO es una query.
Un `search_*` que no encuentra nada es un resultado válido, no un fallo.
"""

from __future__ import annotations

from typing import Any

# Verbos de acción en el INTENT del usuario. Una acción contra el ERP siempre
# pasa por una @tool (escribe en BD); si no se invocó ninguna, no se ejecutó.
_ACTION_INTENT_KW = (
    "crea ",
    "crear",
    "genera",
    "generar",
    "emite",
    "emitir",
    "actualiza",
    "actualizar",
    "modifica",
    "modificar",
    "cambia ",
    "cambiar",
    "elimina",
    "eliminar",
    "borra ",
    "borrar",
    "envia",
    "envía",
    "enviar",
    "manda ",
    "mandar",
    "paga ",
    "pagar",
    "marca ",
    "marcar",
    "da de alta",
    "dar de alta",
    "alta de",
    "registra",
    "registrar",
    "añade",
    "añadir",
    "agrega",
    "agregar",
    "concilia",
    "conciliar",
    "calcula",
    "calcular",
    "aprueba",
    "aprobar",
    "asigna",
    "asignar",
    "reconcilia",
    "abre ",
    "abrir",
    "publica ",
    "publicar",
)

# Frases INEQUÍVOCAS de fallo en la respuesta del LLM.
_FAIL_PHRASES = (
    "no se pudo",
    "no fue posible",
    "no he podido",
    "no puedo completar",
    "falló",
    "fallo al",
    "imposible",
    "problema técnico",
    "uuid malformado",
    "no such tool",
    "necesito el nif",
    "necesito que me proporciones",
    "podrías proporcionarme",
    "podrías proporcionármelo",
)

# Refusal de herramientas: el LLM dice que sus tools no están disponibles. Solo
# cuenta si menciona "herramienta"/"tool" (para no confundir con "el campo X no
# está disponible" en una respuesta legítima).
_TOOL_REFUSAL_PHRASES = (
    "no están disponibles",
    "no disponibles en mi contexto",
    "no tengo acceso a",
    "no está disponible",
    "no dispongo de",
    "no cuento con",
)

# Ambiguas: solo fallo cuando la operación NO es una consulta.
_NOT_FOUND_PHRASES = (
    "no se encontró",
    "no se ha encontrado",
    "no encontrado",
    "no existe",
)


def tool_was_invoked(messages: list[Any]) -> bool:
    """True si algún AIMessage del historial invocó al menos una herramienta."""
    for m in messages or ():
        if getattr(m, "tool_calls", None):
            return True
    return False


# Marcadores en el NOMBRE de la tool que implican MUTACIÓN (escritura en BD). Un
# intent de acción debe disparar una de estas; si solo dispara tools de lectura
# (get_*/list_*/find_*/search_*) y luego "narra" el éxito, es un phantom-write.
# Excluidos a propósito: "pay" (colisiona con list_payrolls, lectura) y "generate"
# (ambiguo). "create" ya cubre calculate_and_create_payroll. Ver lessons 2026-06-23.
_WRITE_TOOL_MARKERS = (
    "create",
    "update",
    "delete",
    "remove",
    "send",
    "register",
    "add",
    "upsert",
    "approve",
    "reconcile",
    "propose",
    "import",
)


def write_tool_was_invoked(messages: list[Any]) -> bool:
    """True si alguna tool invocada parece de ESCRITURA (mutación), no solo lectura."""
    for m in messages or ():
        for tc in getattr(m, "tool_calls", None) or ():
            name = (tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")) or ""
            if any(mk in name.lower() for mk in _WRITE_TOOL_MARKERS):
                return True
    return False


def detect_failure(
    messages: list[Any],
    final_text: str,
    intent: str | None,
    *,
    strict_not_found: bool = False,
) -> tuple[bool, str | None]:
    """Decide si la ejecución del agente fue un fallo.

    Devuelve `(is_error, error_text)`. `error_text` es `None` cuando no hay fallo.
    """
    text = (final_text or "").strip()
    if not text:
        return True, "El agente no devolvió ninguna respuesta."

    low = text.lower()
    if low.startswith("error"):
        return True, final_text
    if any(p in low for p in _FAIL_PHRASES):
        return True, final_text
    if ("herramienta" in low or "tool" in low) and any(p in low for p in _TOOL_REFUSAL_PHRASES):
        return True, final_text
    if strict_not_found and any(p in low for p in _NOT_FOUND_PHRASES):
        return True, final_text

    # Señal estructurada principal: acción pedida pero NINGUNA tool de ESCRITURA
    # invocada. Antes se exigía "0 tools" (any), pero un phantom-write dispara una
    # tool de LECTURA (get_*/list_*) y narra el éxito → se colaba como success=True.
    # Para un intent de acción exigimos una tool de mutación. Ver lessons 2026-06-23.
    intent_low = (intent or "").lower()
    if any(kw in intent_low for kw in _ACTION_INTENT_KW) and not write_tool_was_invoked(messages):
        if tool_was_invoked(messages):
            return True, (
                "La operación no se ejecutó: el agente solo consultó datos pero no invocó "
                "ninguna herramienta de escritura (posible respuesta fabricada)."
            )
        return True, (
            "La operación no se ejecutó: el agente no invocó ninguna herramienta "
            "(posible rechazo del LLM a usar las tools)."
        )

    return False, None
