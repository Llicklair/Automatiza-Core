"""
Agente RAG — Autónomo con LangGraph.

El LLM decide qué herramientas usar según la intención del usuario:
  - Buscar en documentos → search_documents
  - Responder preguntas sobre documentos → answer_from_documents
  - Listar documentos disponibles → list_tenant_documents
"""
import logging
import uuid

import sqlalchemy as sa
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from datetime import datetime

from app.agents.agent_tools.documents import (
    create_document,
    get_document_content,
    list_tenant_documents,
)
from app.agents.agent_tools.knowledge import get_tenant_knowledge, upsert_tenant_knowledge
from app.agents.base import AgentState
from app.agents.types import StepResult
from app.core.config import settings
from app.core.llm_factory import get_llm, get_embedder
from app.db.base import AsyncSessionLocal
from app.db.models.embeddings import DocumentEmbedding

logger = logging.getLogger(__name__)


def _get_llm():
    return get_llm(temperature=0)


# ─── Herramientas del agente ──────────────────────────────────────────────────

@tool
async def search_documents(tenant_id: str, query: str, top_k: int = 5) -> str:
    """
    Busca fragmentos relevantes en los documentos del tenant usando búsqueda
    híbrida: nombre de archivo + búsqueda semántica con pgvector.
    Devuelve los fragmentos más relevantes con sus fuentes.

    Args:
        tenant_id: ID del tenant
        query: Texto de búsqueda en lenguaje natural
        top_k: Número máximo de fragmentos a devolver (por defecto 5)
    """
    return await _search_documents_async(tenant_id, query, top_k)


async def _search_documents_async(tenant_id: str, query: str, top_k: int) -> str:
    from app.db.models.models import TenantDocument

    retrieved_chunks = []
    source_names = set()

    try:
        async with AsyncSessionLocal() as db:
            # Búsqueda literal en nombres de archivo
            stmt_files = sa.select(TenantDocument).where(
                TenantDocument.tenant_id == uuid.UUID(tenant_id),
                sa.or_(
                    TenantDocument.file_name.ilike(f"%{query}%"),
                    TenantDocument.category.ilike(f"%{query}%"),
                )
            ).limit(2)
            res_files = await db.execute(stmt_files)
            for fd in res_files.scalars().all():
                source_names.add(fd.file_name)
                retrieved_chunks.append(
                    f"📄 {fd.file_name} [{fd.category}]: {fd.parsed_content[:500] if fd.parsed_content else 'Sin contenido extraído'}"
                )

            # Búsqueda semántica con pgvector
            embedder = get_embedder()
            if embedder:
                query_vector = await embedder.aembed_query(query)
                stmt_vector = sa.select(DocumentEmbedding).where(
                    DocumentEmbedding.tenant_id == uuid.UUID(tenant_id)
                ).order_by(
                    DocumentEmbedding.embedding.cosine_distance(query_vector)
                ).limit(top_k)

                res_vector = await db.execute(stmt_vector)
                for match in res_vector.scalars().all():
                    doc_name_res = await db.execute(
                        sa.select(TenantDocument.file_name).where(TenantDocument.id == match.document_id)
                    )
                    doc_name = doc_name_res.scalar()
                    if doc_name:
                        source_names.add(doc_name)
                    retrieved_chunks.append(match.text_content)
    except Exception as e:
        return f"Error en búsqueda: {e}"

    if not retrieved_chunks:
        return f"No se encontraron documentos relevantes para: '{query}'"

    result = f"Fragmentos encontrados ({len(retrieved_chunks)}) de {len(source_names)} documento(s):\n"
    result += f"Fuentes: {', '.join(source_names)}\n\n"
    for idx, chunk in enumerate(retrieved_chunks, 1):
        result += f"--- Fragmento {idx} ---\n{chunk[:500]}\n\n"
    return result


@tool
async def answer_from_documents(tenant_id: str, question: str, top_k: int = 5) -> str:
    """
    Responde una pregunta del usuario basándose ÚNICAMENTE en los documentos
    almacenados en el sistema. Busca fragmentos relevantes y genera una respuesta
    fundamentada con fuentes.

    Args:
        tenant_id: ID del tenant
        question: Pregunta del usuario en lenguaje natural
        top_k: Número de fragmentos de contexto a usar (por defecto 5)
    """
    return await _answer_from_documents_async(tenant_id, question, top_k)


async def _answer_from_documents_async(tenant_id: str, question: str, top_k: int) -> str:
    from app.db.models.models import TenantDocument

    # Buscar fragmentos relevantes
    retrieved_chunks = []
    source_names = set()

    try:
        async with AsyncSessionLocal() as db:
            # Búsqueda por nombre
            stmt_files = sa.select(TenantDocument).where(
                TenantDocument.tenant_id == uuid.UUID(tenant_id),
                sa.or_(
                    TenantDocument.file_name.ilike(f"%{question}%"),
                    TenantDocument.category.ilike(f"%{question}%"),
                )
            ).limit(2)
            res_files = await db.execute(stmt_files)
            for fd in res_files.scalars().all():
                source_names.add(fd.file_name)
                retrieved_chunks.append({
                    "doc_id": str(fd.id),
                    "text": f"Documento: {fd.file_name}. Categoría: {fd.category}. Contenido: {fd.parsed_content[:500] if fd.parsed_content else 'N/A'}"
                })

            # Búsqueda semántica
            embedder = get_embedder()
            if embedder:
                query_vector = await embedder.aembed_query(question)
                stmt_vector = sa.select(DocumentEmbedding).where(
                    DocumentEmbedding.tenant_id == uuid.UUID(tenant_id)
                ).order_by(
                    DocumentEmbedding.embedding.cosine_distance(query_vector)
                ).limit(top_k)

                res_vector = await db.execute(stmt_vector)
                for match in res_vector.scalars().all():
                    doc_name_res = await db.execute(
                        sa.select(TenantDocument.file_name).where(TenantDocument.id == match.document_id)
                    )
                    doc_name = doc_name_res.scalar()
                    if doc_name:
                        source_names.add(doc_name)
                    retrieved_chunks.append({"doc_id": str(match.document_id), "text": match.text_content})
    except Exception as e:
        return f"Error buscando documentos: {e}"

    if not retrieved_chunks:
        return "No he encontrado documentos en tu base de datos que contengan información relevante para responder esta pregunta."

    # Construir contexto y responder con LLM
    contexto = ""
    for idx, c in enumerate(retrieved_chunks, 1):
        contexto += f"\n--- Fragmento {idx} ---\n{c['text']}\n"

    llm = _get_llm()
    try:
        response = await llm.ainvoke([
            SystemMessage(content="Eres un asistente empresarial experto. Responde ÚNICAMENTE basándote en los fragmentos proporcionados. Si no puedes responder, dilo claramente. Nunca inventes datos."),
            HumanMessage(content=f"DOCUMENTOS:\n{contexto}\n\nPREGUNTA: {question}"),
        ])
        answer = response.content
    except Exception as e:
        return f"Error generando respuesta: {e}"

    sources_str = ", ".join(source_names) if source_names else "documentos del sistema"
    return f"{answer}\n\n📎 Fuentes: {sources_str} ({len(retrieved_chunks)} fragmentos consultados)"


# ─── Lista de herramientas ────────────────────────────────────────────────────

tools = [
    search_documents,
    answer_from_documents,
    create_document,
    list_tenant_documents,
    get_document_content,
    get_tenant_knowledge,
    upsert_tenant_knowledge,
]


# ─── Nodos del grafo LangGraph ───────────────────────────────────────────────

RAG_SYSTEM_PROMPT = """Eres el Agente de Consulta Documental (RAG) de un ERP para PYMEs españolas. Tus capacidades:

1. **Buscar documentos** con `search_documents` — búsqueda semántica en documentos del tenant.
2. **Responder preguntas** con `answer_from_documents` — responde basándose en documentos reales.
3. **Listar documentos** con `list_tenant_documents` — ver documentos disponibles.
4. **Leer documentos** con `get_document_content` — ver contenido de un documento específico.
5. **Crear documentos** con `create_document` — generar resúmenes o informes.
6. **Memoria del tenant** con `get_tenant_knowledge` y `upsert_tenant_knowledge`.

REGLAS:
- Si el usuario pregunta algo sobre sus documentos, usa `answer_from_documents`.
- Si quiere buscar o encontrar documentos, usa `search_documents`.
- NUNCA inventes información. Solo responde con datos de los documentos.
- Si no hay documentos relevantes, dilo claramente.
- Responde siempre en español.

ID del Tenant actual: {tenant_id}"""


async def rag_agent_node(state: AgentState):
    if "messages" not in state or not state["messages"]:
        sys_msg = SystemMessage(
            content=RAG_SYSTEM_PROMPT.format(tenant_id=state.get("tenant_id", ""))
        )
        user_msg = HumanMessage(content=state["user_intent"])
        extra_init_messages = [sys_msg, user_msg]
        state["messages"] = extra_init_messages
    else:
        extra_init_messages = []

    llm_with_tools = _get_llm().bind_tools(tools)
    response = await llm_with_tools.ainvoke(state["messages"])

    result_log = StepResult(
        step_id=f"rag_step_{datetime.now().timestamp()}",
        description="Procesando consulta documental...",
        status="completed",
        action_taken="Buscando en documentos" if response.tool_calls else "Consulta documental completada.",
    )

    if "agent_results" not in state:
        state["agent_results"] = []
    state["agent_results"].append(result_log.model_dump())
    return {"messages": extra_init_messages + [response], "agent_results": state["agent_results"]}


def rag_finalize_node(state: AgentState):
    last_msg = state["messages"][-1]
    final_result = StepResult(
        step_id="rag_final",
        description="Agente RAG ha finalizado.",
        status="completed",
        action_taken=last_msg.content if isinstance(last_msg.content, str) else "Consulta documental completada.",
    )
    return {"status": "done", "agent_results": [final_result.model_dump()]}


# ─── Compilar grafo ───────────────────────────────────────────────────────────

workflow = StateGraph(AgentState)
workflow.add_node("rag_agent", rag_agent_node)
workflow.add_node("tools", ToolNode(tools))
workflow.add_node("finalize", rag_finalize_node)

workflow.set_entry_point("rag_agent")
workflow.add_conditional_edges("rag_agent", tools_condition)
workflow.add_edge("tools", "rag_agent")

graph = workflow.compile()
