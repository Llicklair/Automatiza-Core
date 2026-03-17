"""
Utilidades para compatibilidad con Gemini (Google Generative AI).
Gemini exige que cada AIMessage con tool_calls vaya seguida inmediatamente
por un ToolMessage por cada llamada. Este módulo sanitiza el historial.
"""
from langchain_core.messages import AIMessage, ToolMessage


def _sanitize_messages_for_gemini(messages: list) -> list:
    """
    Gemini exige que cada AIMessage con tool_calls vaya seguido inmediatamente
    por un ToolMessage por cada llamada. Si hay huérfanos (tool_calls sin su
    ToolMessage correspondiente), los elimina para evitar el error 400.
    """
    sanitized = []
    i = 0
    while i < len(messages):
        msg = messages[i]
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            expected_ids = {tc["id"] for tc in msg.tool_calls}
            following_tool_ids = set()
            j = i + 1
            while j < len(messages) and isinstance(messages[j], ToolMessage):
                following_tool_ids.add(messages[j].tool_call_id)
                j += 1
            if expected_ids.issubset(following_tool_ids):
                sanitized.append(msg)
            else:
                if isinstance(msg.content, str) and msg.content.strip():
                    sanitized.append(AIMessage(content=msg.content))
        else:
            sanitized.append(msg)
        i += 1
    return sanitized


class GeminiSafeWrapper:
    """
    Envuelve cualquier LLM para sanitizar el historial de mensajes antes
    de cada llamada. Necesario para cumplir las restricciones de turno de Gemini.
    Delega bind_tools, with_fallbacks y cualquier otro atributo al LLM base.
    """

    def __init__(self, base_llm):
        self._base = base_llm

    def bind_tools(self, tools, **kwargs):
        return GeminiSafeWrapper(self._base.bind_tools(tools, **kwargs))

    def with_fallbacks(self, fallbacks, **kwargs):
        return GeminiSafeWrapper(self._base.with_fallbacks(fallbacks, **kwargs))

    def with_structured_output(self, schema, **kwargs):
        return self._base.with_structured_output(schema, **kwargs)

    def invoke(self, messages, **kwargs):
        if isinstance(messages, list):
            messages = _sanitize_messages_for_gemini(messages)
        return self._base.invoke(messages, **kwargs)

    async def ainvoke(self, messages, **kwargs):
        if isinstance(messages, list):
            messages = _sanitize_messages_for_gemini(messages)
        return await self._base.ainvoke(messages, **kwargs)

    def __getattr__(self, name):
        return getattr(self._base, name)
