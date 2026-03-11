from typing import Any, TypedDict, Annotated
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    # Identidad
    tenant_id: str
    task_id: str | None
    user_id: str | None

    # Intención del usuario
    user_intent: str
    current_intent: str   # puede diferir de user_intent en planes multiagente

    # Mensajes LangChain (lista de HumanMessage / AIMessage / ToolMessage)
    # Usamos add_messages para que LangGraph acumule el histórico automáticamente
    messages: Annotated[list[Any], add_messages]

    # Resultados acumulados de los pasos del agente
    agent_results: list[dict]

    # Estado de finalización
    status: str   # "running" | "done" | "failed"
