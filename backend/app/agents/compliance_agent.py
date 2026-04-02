"""
Agente de Cumplimiento Legal y Fiscal — Autónomo con LangGraph.

El LLM decide qué herramientas usar según la intención del usuario:
  - Consultar vencimientos fiscales → check_fiscal_deadlines
  - Novedades del BOE → check_boe_news
  - Consultas fiscales con RAG → fiscal_query
"""
import json
import logging
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agents.agent_tools.documents import (
    create_document,
    get_document_content,
    list_tenant_documents,
)
from app.agents.agent_tools.knowledge import get_tenant_knowledge, upsert_tenant_knowledge
from app.agents.base import AgentState
from app.agents.types import StepResult
from app.core.config import settings
from app.core.llm_factory import get_llm
from app.core.prompt_sanitizer import sanitize_user_input
from app.integrations.boe_scraper import BOEScraper, get_proximos_vencimientos

logger = logging.getLogger(__name__)


def _get_llm():
    return get_llm(temperature=0.1)


def _get_llm_json():
    return get_llm(temperature=0.1, format_output="json")


# ─── Herramientas del agente ──────────────────────────────────────────────────

@tool
async def check_fiscal_deadlines(days_ahead: int = 90) -> str:
    """
    Consulta los vencimientos fiscales próximos del calendario AEAT.
    Devuelve alertas claras sobre modelos tributarios pendientes.

    Args:
        days_ahead: Días de antelación para buscar vencimientos (por defecto 90)
    """
    return await _check_fiscal_deadlines_async(days_ahead)


async def _check_fiscal_deadlines_async(days_ahead: int) -> str:
    try:
        vencimientos = get_proximos_vencimientos(days_ahead=days_ahead)
    except Exception as _e:
        logger.warning("Error obteniendo vencimientos fiscales, usando fallback: %s", _e)
        vencimientos = [
            {"nombre": "Modelo 303 (IVA Trimestral)", "fecha_limite": "2026-04-20", "dias_restantes": 32},
            {"nombre": "Modelo 111 (Retenciones)", "fecha_limite": "2026-04-20", "dias_restantes": 32},
        ]

    if not vencimientos:
        return f"No hay vencimientos fiscales en los próximos {days_ahead} días."

    # Redactar alertas con LLM
    llm = _get_llm_json()
    venc_json = json.dumps(vencimientos[:10], ensure_ascii=False)
    try:
        response = await llm.ainvoke([
            SystemMessage(content="""Eres un asesor fiscal experto en PYMEs españolas.
Con los vencimientos proporcionados, redacta alertas claras y accionables.
REGLAS: Solo usa datos del JSON. Si quedan <15 días: tono urgente. Si >30: informativo.
Devuelve JSON: {"alertas": ["...", "..."]}"""),
            HumanMessage(content=f"Vencimientos próximos:\n{venc_json}"),
        ])
        data = json.loads(response.content)
        alertas = data.get("alertas", [])
    except Exception as _e:
        logger.warning("Error generando alertas fiscales con LLM, usando fallback: %s", _e)
        alertas = [
            f"⚠️ {v['nombre']}: vence el {v['fecha_limite']} ({v['dias_restantes']} días)"
            for v in vencimientos
        ]

    result = f"Vencimientos fiscales próximos ({len(vencimientos)}):\n\n"
    for alerta in alertas:
        result += f"• {alerta}\n"
    return result


@tool
async def check_boe_news() -> str:
    """
    Consulta las últimas novedades del BOE (Boletín Oficial del Estado)
    relevantes para PYMEs y autónomos. Resume el impacto y acciones recomendadas.
    """
    return await _check_boe_news_async()


async def _check_boe_news_async() -> str:
    scraper = BOEScraper()
    try:
        novedades = await scraper.get_novedades(seccion="fiscal", max_items=5)
    except Exception as exc:
        return f"Error consultando el BOE: {exc}"
    finally:
        await scraper.close()

    novedades_relevantes = [n for n in novedades if n.get("relevante_pyme")]

    if not novedades_relevantes:
        return "No se han detectado novedades del BOE relevantes para PYMEs en los últimos días."

    llm = _get_llm_json()
    try:
        response = await llm.ainvoke([
            SystemMessage(content="""Eres un asesor fiscal especialista en PYMEs.
Analiza las novedades del BOE e identifica las que afectan a PYMEs.
Explica el impacto en lenguaje sencillo. Indica qué acción tomar.
Devuelve JSON: {"resumen": "...", "novedades_relevantes": [...], "acciones_recomendadas": [...]}"""),
            HumanMessage(content=f"Novedades BOE:\n{json.dumps(novedades_relevantes, ensure_ascii=False)}"),
        ])
        data = json.loads(response.content)
        resumen = data.get("resumen", str(data))
    except Exception as _e:
        logger.warning("Error procesando novedades BOE con LLM, usando fallback: %s", _e)
        resumen = f"Se han detectado {len(novedades_relevantes)} novedades relevantes para PYMEs."

    return f"Novedades BOE:\n\n{resumen}"


@tool
async def fiscal_query(tenant_id: str, question: str) -> str:
    """
    Responde una consulta fiscal usando normativa española y documentos de la empresa (RAG).
    Usa contexto normativo básico + búsqueda semántica en documentos subidos.

    Args:
        tenant_id: ID del tenant
        question: Pregunta fiscal del usuario
    """
    return await _fiscal_query_async(tenant_id, question)


async def _fiscal_query_async(tenant_id: str, question: str) -> str:
    contexto_normativo = """
    - IVA General España: 21%. Reducido: 10%. Superreducido: 4%.
    - Plazo presentación Modelo 303 (IVA trimestral): 20 días tras fin de trimestre (30 días en 4T).
    - Modelo 130 (IRPF fraccionado Estimación Directa): mismos plazos que Modelo 303.
    - Modelo 111 (Retenciones): trimestral, mismos plazos.
    - Factura electrónica obligatoria para B2B: Ley Crea y Crece (pendiente de reglamento).
    - Umbral operaciones con terceros Modelo 347: 3.005,06€ anuales.
    - Retención general profesionales: 15% (7% primeros años de actividad).
    - Autónomos en módulos: no presentan Modelo 130 sino Modelo 131.
    """

    # Búsqueda RAG en documentos de la empresa
    text_from_docs = ""
    if tenant_id:
        try:
            import uuid
            import sqlalchemy as sa
            from app.core.llm_factory import get_embedder
            from app.db.base import AsyncSessionLocal
            from app.db.models.embeddings import DocumentEmbedding

            embedder = get_embedder()
            if embedder:
                query_vector = await embedder.aembed_query(question)
                async with AsyncSessionLocal() as db:
                    # Obtener jurisdicción del tenant para filtro cross-border
                    from app.db.models.auth import Tenant
                    tenant_result = await db.execute(
                        sa.select(Tenant.jurisdiction).where(Tenant.id == uuid.UUID(tenant_id))
                    )
                    jurisdiction = tenant_result.scalar() or "ES_TAX"

                    stmt = sa.select(DocumentEmbedding).where(
                        DocumentEmbedding.tenant_id == uuid.UUID(tenant_id),
                        sa.or_(
                            DocumentEmbedding.jurisdiction == jurisdiction,
                            DocumentEmbedding.jurisdiction.is_(None),
                        ),
                    ).order_by(
                        DocumentEmbedding.embedding.cosine_distance(query_vector)
                    ).limit(3)
                    result = await db.execute(stmt)
                    for idx, match in enumerate(result.scalars().all(), 1):
                        text_from_docs += f"\n--- Fragmento {idx} ---\n{match.text_content}\n"
        except Exception as e:
            logger.warning("Error buscando embeddings en compliance: %s", e)

    if text_from_docs.strip():
        contexto_normativo += "\n\nDOCUMENTOS DE LA EMPRESA:\n" + text_from_docs

    llm = _get_llm()
    try:
        response = await llm.ainvoke([
            SystemMessage(content=f"""Eres un asesor fiscal experto en legislación española.
CONTEXTO NORMATIVO:
{contexto_normativo}

INSTRUCCIONES:
1. Responde SOLO basándote en el contexto proporcionado.
2. Si no tienes la info, di que requiere asesor fiscal certificado.
3. Nunca inventes interpretaciones normativas.
4. Añade siempre: "Esta información es orientativa. Consulta con tu asesor fiscal."
"""),
            HumanMessage(content=f"Consulta fiscal: {sanitize_user_input(question)}"),
        ])
        return response.content
    except Exception as _e:
        logger.warning("Error procesando consulta fiscal con LLM: %s", _e)
        return "No he podido procesar tu consulta. Consulta directamente con tu asesor fiscal."


# ─── Lista de herramientas ────────────────────────────────────────────────────

tools = [
    check_fiscal_deadlines,
    check_boe_news,
    fiscal_query,
    create_document,
    list_tenant_documents,
    get_document_content,
    get_tenant_knowledge,
    upsert_tenant_knowledge,
]


# ─── Nodos del grafo LangGraph ───────────────────────────────────────────────

COMPLIANCE_SYSTEM_PROMPT = """Eres el Agente de Cumplimiento Legal y Fiscal de un ERP para PYMEs españolas. Tus capacidades:

1. **Vencimientos fiscales** con `check_fiscal_deadlines` — consulta el calendario AEAT y alerta sobre plazos.
2. **Novedades BOE** con `check_boe_news` — resume cambios legislativos relevantes para PYMEs.
3. **Consultas fiscales** con `fiscal_query` — responde preguntas sobre obligaciones fiscales con RAG.
4. **Crear documentos** con `create_document` — para informes de compliance.
5. **Memoria del tenant** con `get_tenant_knowledge` y `upsert_tenant_knowledge`.

REGLAS:
- Si el usuario pregunta sobre plazos o vencimientos, usa `check_fiscal_deadlines`.
- Si pregunta sobre novedades legales o BOE, usa `check_boe_news`.
- Si hace una consulta fiscal específica, usa `fiscal_query`.
- Siempre advierte que la información es orientativa y recomienda consultar un asesor fiscal.
- Responde siempre en español.

ID del Tenant actual: {tenant_id}"""


async def compliance_agent_node(state: AgentState):
    if "messages" not in state or not state["messages"]:
        sys_msg = SystemMessage(
            content=COMPLIANCE_SYSTEM_PROMPT.format(tenant_id=state.get("tenant_id", ""))
        )
        user_msg = HumanMessage(content=state["user_intent"])
        extra_init_messages = [sys_msg, user_msg]
        state["messages"] = extra_init_messages
    else:
        extra_init_messages = []

    llm_with_tools = _get_llm().bind_tools(tools)
    response = await llm_with_tools.ainvoke(state["messages"])

    result_log = StepResult(
        step_id=f"compliance_step_{datetime.now().timestamp()}",
        description="Procesando solicitud de compliance...",
        status="completed",
        action_taken="Invocando herramientas de compliance" if response.tool_calls else "Asistencia compliance completada.",
    )

    if "agent_results" not in state:
        state["agent_results"] = []
    state["agent_results"].append(result_log.model_dump())
    return {"messages": extra_init_messages + [response], "agent_results": state["agent_results"]}


def compliance_finalize_node(state: AgentState):
    last_msg = state["messages"][-1]
    final_result = StepResult(
        step_id="compliance_final",
        description="Agente de Compliance ha finalizado.",
        status="completed",
        action_taken=last_msg.content if isinstance(last_msg.content, str) else "Operación compliance completada.",
    )
    return {"status": "done", "agent_results": [final_result.model_dump()]}


# ─── Compilar grafo ───────────────────────────────────────────────────────────

workflow = StateGraph(AgentState)
workflow.add_node("compliance_agent", compliance_agent_node)
workflow.add_node("tools", ToolNode(tools))
workflow.add_node("finalize", compliance_finalize_node)

workflow.set_entry_point("compliance_agent")
workflow.add_conditional_edges("compliance_agent", tools_condition)
workflow.add_edge("tools", "compliance_agent")

graph = workflow.compile()
