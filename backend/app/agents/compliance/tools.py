"""
Compliance agent — tools: vencimientos fiscales, BOE y consultas RAG.
"""

from __future__ import annotations

import json
import logging
import uuid

import sqlalchemy as sa
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from app.agents.agent_tools.documents import (
    create_document,
    get_document_content,
    list_tenant_documents,
)
from app.agents.agent_tools.knowledge import get_tenant_knowledge, upsert_tenant_knowledge
from app.core.llm_factory import get_embedder, get_llm
from app.core.prompt_sanitizer import sanitize_user_input
from app.db.base import AsyncSessionLocal
from app.db.models.auth import Tenant
from app.db.models.embeddings import DocumentEmbedding
from app.integrations.boe_scraper import BOEScraper, get_proximos_vencimientos

logger = logging.getLogger(__name__)


def _get_llm():
    return get_llm(temperature=0.1)


def _get_llm_json():
    return get_llm(temperature=0.1, format_output="json")


@tool
async def check_fiscal_deadlines(days_ahead: int = 90) -> str:
    """
    Consulta los vencimientos fiscales próximos del calendario AEAT.
    Devuelve alertas claras sobre modelos tributarios pendientes.

    Args:
        days_ahead: Días de antelación para buscar vencimientos (por defecto 90)
    """
    try:
        vencimientos = get_proximos_vencimientos(days_ahead=days_ahead)
    except Exception as e:
        logger.warning("Error obteniendo vencimientos fiscales, usando fallback: %s", e)
        vencimientos = [
            {
                "nombre": "Modelo 303 (IVA Trimestral)",
                "fecha_limite": "2026-04-20",
                "dias_restantes": 32,
            },
            {
                "nombre": "Modelo 111 (Retenciones)",
                "fecha_limite": "2026-04-20",
                "dias_restantes": 32,
            },
        ]

    if not vencimientos:
        return f"No hay vencimientos fiscales en los próximos {days_ahead} días."

    llm = _get_llm_json()
    venc_json = json.dumps(vencimientos[:10], ensure_ascii=False)
    try:
        response = await llm.ainvoke(
            [
                SystemMessage(
                    content="""Eres un asesor fiscal experto en PYMEs españolas.
Con los vencimientos proporcionados, redacta alertas claras y accionables.
REGLAS: Solo usa datos del JSON. Si quedan <15 días: tono urgente. Si >30: informativo.
Devuelve JSON: {"alertas": ["...", "..."]}"""
                ),
                HumanMessage(content=f"Vencimientos próximos:\n{venc_json}"),
            ]
        )
        data = json.loads(response.content)
        alertas = data.get("alertas", [])
    except Exception as e:
        logger.warning("Error generando alertas fiscales con LLM, usando fallback: %s", e)
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
    Consulta las últimas novedades del BOE relevantes para PYMEs y autónomos.
    Resume el impacto y acciones recomendadas.
    """
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
        response = await llm.ainvoke(
            [
                SystemMessage(
                    content="""Eres un asesor fiscal especialista en PYMEs.
Analiza las novedades del BOE e identifica las que afectan a PYMEs.
Explica el impacto en lenguaje sencillo. Indica qué acción tomar.
Devuelve JSON: {"resumen": "...", "novedades_relevantes": [...], "acciones_recomendadas": [...]}"""
                ),
                HumanMessage(
                    content=f"Novedades BOE:\n{json.dumps(novedades_relevantes, ensure_ascii=False)}"
                ),
            ]
        )
        data = json.loads(response.content)
        resumen = data.get("resumen", str(data))
    except Exception as e:
        logger.warning("Error procesando novedades BOE con LLM, usando fallback: %s", e)
        resumen = f"Se han detectado {len(novedades_relevantes)} novedades relevantes para PYMEs."

    return f"Novedades BOE:\n\n{resumen}"


_CONTEXTO_NORMATIVO = """
    - IVA General España: 21%. Reducido: 10%. Superreducido: 4%.
    - Plazo presentación Modelo 303 (IVA trimestral): 20 días tras fin de trimestre (30 días en 4T).
    - Modelo 130 (IRPF fraccionado Estimación Directa): mismos plazos que Modelo 303.
    - Modelo 111 (Retenciones): trimestral, mismos plazos.
    - Factura electrónica obligatoria para B2B: Ley Crea y Crece (pendiente de reglamento).
    - Umbral operaciones con terceros Modelo 347: 3.005,06€ anuales.
    - Retención general profesionales: 15% (7% primeros años de actividad).
    - Autónomos en módulos: no presentan Modelo 130 sino Modelo 131.
    """


async def _search_tenant_docs(tenant_id: str, question: str) -> str:
    """Busca fragmentos relevantes en los documentos del tenant via RAG. Devuelve texto o vacío."""
    try:
        embedder = get_embedder()
        if not embedder:
            return ""
        query_vector = await embedder.aembed_query(question)
        async with AsyncSessionLocal() as db:
            tenant_result = await db.execute(
                sa.select(Tenant.jurisdiction).where(Tenant.id == uuid.UUID(tenant_id))
            )
            jurisdiction = tenant_result.scalar() or "ES_TAX"
            stmt = (
                sa.select(DocumentEmbedding)
                .where(
                    DocumentEmbedding.tenant_id == uuid.UUID(tenant_id),
                    sa.or_(
                        DocumentEmbedding.jurisdiction == jurisdiction,
                        DocumentEmbedding.jurisdiction.is_(None),
                    ),
                )
                .order_by(DocumentEmbedding.embedding.cosine_distance(query_vector))
                .limit(3)
            )
            result = await db.execute(stmt)
            fragments = result.scalars().all()
        return "".join(
            f"\n--- Fragmento {i} ---\n{m.text_content}\n" for i, m in enumerate(fragments, 1)
        )
    except Exception as e:
        logger.warning("Error buscando embeddings en compliance: %s", e)
        return ""


@tool
async def fiscal_query(tenant_id: str, question: str) -> str:
    """
    Responde una consulta fiscal usando normativa española y documentos de la empresa (RAG).

    Args:
        tenant_id: ID del tenant
        question: Pregunta fiscal del usuario
    """
    contexto = _CONTEXTO_NORMATIVO
    if tenant_id:
        docs_text = await _search_tenant_docs(tenant_id, question)
        if docs_text.strip():
            contexto += "\n\nDOCUMENTOS DE LA EMPRESA:\n" + docs_text

    llm = _get_llm()
    try:
        response = await llm.ainvoke(
            [
                SystemMessage(
                    content=f"""Eres un asesor fiscal experto en legislación española.
CONTEXTO NORMATIVO:
{contexto}

INSTRUCCIONES:
1. Responde SOLO basándote en el contexto proporcionado.
2. Si no tienes la info, di que requiere asesor fiscal certificado.
3. Nunca inventes interpretaciones normativas.
4. Añade siempre: "Esta información es orientativa. Consulta con tu asesor fiscal."
"""
                ),
                HumanMessage(content=f"Consulta fiscal: {sanitize_user_input(question)}"),
            ]
        )
        return response.content
    except Exception as e:
        logger.warning("Error procesando consulta fiscal con LLM: %s", e)
        return "No he podido procesar tu consulta. Consulta directamente con tu asesor fiscal."


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


# Defensa multi-tenant: envolver tools para forzar tenant_id del ContextVar
from app.agents.tenant_context import isolated as _isolated
tools = _isolated(tools)
