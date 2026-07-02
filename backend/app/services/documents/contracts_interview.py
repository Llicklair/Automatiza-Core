"""Asistente conversacional de contratos (entrevista guiada por LLM).

El LLM entrevista al usuario una pregunta a la vez para reunir los datos del
contrato elegido y, al terminar, redacta el contrato profesional español
completo (sin placeholders) precedido por el marcador `=== CONTRATO FINALIZADO ===`.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

FINAL_MARKER = "=== CONTRATO FINALIZADO ==="

# Tipos de contrato soportados y su categoría documental al guardar.
CONTRACT_TYPES: dict[str, dict[str, str]] = {
    "servicios": {"label": "Contrato de Prestación de Servicios", "category": "otros"},
    "trabajo": {"label": "Contrato de Trabajo", "category": "rrhh"},
    "nda": {"label": "Acuerdo de Confidencialidad (NDA)", "category": "otros"},
    "alquiler": {"label": "Contrato de Arrendamiento (Alquiler)", "category": "otros"},
}


def _system_prompt(contract_label: str) -> str:
    return (
        "Eres un asistente jurídico español experto en redacción de contratos. "
        f"Vas a ayudar a redactar un «{contract_label}» conforme al derecho español.\n\n"
        "PROTOCOLO DE ENTREVISTA (síguelo estrictamente):\n"
        "1. Haz UNA sola pregunta por turno, en español, clara y concreta, para "
        "reunir los datos imprescindibles (partes con NIF/CIF y domicilio, objeto, "
        "duración, contraprestación/precio, condiciones específicas, jurisdicción...).\n"
        "2. No hagas listas de varias preguntas a la vez. Una pregunta, esperas la "
        "respuesta, y continúas.\n"
        "3. Cuando ya tengas TODOS los datos necesarios, redacta el contrato COMPLETO "
        "y profesional en español, en formato Markdown, SIN placeholders ni corchetes "
        "vacíos (usa los datos reales aportados). Antes del contrato escribe en una "
        f"línea exactamente: {FINAL_MARKER}\n"
        "4. No emitas el marcador hasta que el contrato esté listo y completo.\n"
        "Empieza saludando brevemente y formulando la primera pregunta."
    )


async def run_interview(
    tenant_id,
    db: AsyncSession,
    contract_type: str,
    messages: list[dict],
) -> dict:
    """Avanza la entrevista. Devuelve {message, done, contract}.

    `messages` es el historial [{role: "user"|"assistant", content: str}].
    Si el LLM emite el marcador final, `done=True` y `contract` trae el texto.
    """
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    from app.core.llm_factory import get_llm_for_tenant

    meta = CONTRACT_TYPES.get(contract_type)
    if meta is None:
        raise ValueError(f"Tipo de contrato no soportado: {contract_type}")

    lc_messages = [SystemMessage(content=_system_prompt(meta["label"]))]
    for m in messages:
        role = (m.get("role") or "").lower()
        content = m.get("content") or ""
        if role == "assistant":
            lc_messages.append(AIMessage(content=content))
        else:
            lc_messages.append(HumanMessage(content=content))
    # Si no hay historial, pedimos al modelo que arranque la entrevista.
    if not messages:
        lc_messages.append(HumanMessage(content="Inicia la entrevista para este contrato."))

    llm = await get_llm_for_tenant(tenant_id, db, temperature=0.3)
    response = await llm.ainvoke(lc_messages)
    text = (response.content or "").strip()

    if FINAL_MARKER in text:
        before, _, after = text.partition(FINAL_MARKER)
        contract = after.strip()
        message = before.strip() or "He redactado el contrato. Revísalo y guárdalo si es correcto."
        return {"message": message, "done": True, "contract": contract}

    return {"message": text, "done": False, "contract": None}
