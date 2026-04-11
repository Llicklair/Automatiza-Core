"""
Agente de Marketing — Planificador de contenidos para PYME.

Analiza el catálogo de productos y genera un plan de contenidos mensual
con textos, hashtags, horarios y sugerencias de imagen.
El agente NO publica — solo planifica. El usuario ejecuta manualmente.
"""

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agents.base import AgentState
from app.core.llm_factory import get_llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres el Planificador de Marketing de una PYME española.
Tu misión es generar planes de contenidos para redes sociales (Instagram, Facebook, LinkedIn)
basados en el catálogo real de productos/servicios de la empresa.

REGLAS:
- Devuelve SIEMPRE un JSON válido con la estructura indicada.
- Los textos deben ser en español, cercanos y naturales (no robóticos).
- Incluye emojis relevantes en los textos.
- Los hashtags deben ser en español y relevantes al sector.
- Las sugerencias de imagen deben ser descriptivas pero realizables con un smartphone.
- Sugiere horarios óptimos según la plataforma y el tipo de negocio.
- Si no hay productos, genera contenidos educativos o de marca.

FORMATO DE RESPUESTA (JSON):
{
  "period": "Descripción del período (ej: Semana 1-4 Abril 2026)",
  "focus": "Objetivo del plan (ej: Aumentar ventas, Lanzamiento, Educativo)",
  "posts": [
    {
      "day": "Lunes 7 Abril",
      "platform": "Instagram",
      "product": "Nombre del producto o null",
      "text": "Texto completo del post con emojis",
      "hashtags": ["#hashtag1", "#hashtag2"],
      "best_time": "19:00",
      "image_idea": "Descripción de la imagen sugerida"
    }
  ]
}
"""


@tool
async def get_product_catalog(tenant_id: str) -> str:
    """
    Obtiene el catálogo de productos/servicios del tenant.
    Devuelve nombre, descripción y precio de hasta 20 productos activos.
    """
    from uuid import UUID

    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    from app.db.models.billing import Product

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Product)
                .where(Product.tenant_id == UUID(tenant_id))
                .order_by(Product.created_at.desc())
                .limit(20)
            )
            products = result.scalars().all()

        if not products:
            return "Sin productos registrados. Generar contenido de marca genérico."

        lines = []
        for p in products:
            price = f"{p.price:.2f}€" if p.price else "precio no definido"
            desc = p.description or ""
            lines.append(f"- {p.name} | {price} | {desc[:120]}")
        return "\n".join(lines)

    except Exception as e:
        logger.warning("Error obteniendo catálogo: %s", e)
        return f"Error al obtener catálogo: {e}"


# ── Grafo LangGraph ────────────────────────────────────────────────────────────

_tools = [get_product_catalog]


async def _agent_node(state: AgentState) -> dict:
    llm = get_llm(temperature=0.4).bind_tools(_tools)
    if not state.get("messages"):
        state["messages"] = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=state.get("user_intent", "Genera un plan de contenidos para este mes")
            ),
        ]
    response = await llm.ainvoke(state["messages"])
    return {"messages": [response]}


def _finalize(state: AgentState) -> dict:
    last = state["messages"][-1] if state.get("messages") else None
    content = last.content if last and isinstance(last.content, str) else "Plan generado."
    return {
        "status": "done",
        "agent_results": [{"agent": "marketing", "result": content, "status": "completed"}],
    }


_graph = StateGraph(AgentState)
_graph.add_node("agent", _agent_node)
_graph.add_node("tools", ToolNode(_tools))
_graph.add_node("finalize", _finalize)
_graph.set_entry_point("agent")
_graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", "__end__": "finalize"})
_graph.add_edge("tools", "agent")
_graph.add_edge("finalize", END)

graph = _graph.compile()
