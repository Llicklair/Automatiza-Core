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
from app.agents.agent_tools.reports import create_pdf_report, create_pdf_text_report
from app.core.llm_factory import get_embedder, get_llm
from app.core.prompt_sanitizer import sanitize_user_input
from app.db.base import AsyncSessionLocal
from app.db.models.auth import Tenant
from app.integrations.boe_scraper import BOEScraper, get_proximos_vencimientos

logger = logging.getLogger(__name__)


@tool
async def check_fiscal_deadlines(
    days_ahead: int = 90, tenant_id: str | None = None
) -> str:
    """
    Consulta los vencimientos fiscales próximos del calendario AEAT.
    Devuelve alertas claras sobre modelos tributarios pendientes.

    Args:
        days_ahead: Días de antelación para buscar vencimientos (por defecto 90)
        tenant_id: aceptado por consistencia con otras tools; el calendario
            AEAT es nacional y no se filtra por tenant.
    """
    _ = tenant_id  # accepted but unused: AEAT calendar is the same for all tenants
    try:
        vencimientos = get_proximos_vencimientos(days_ahead=days_ahead)
    except Exception as e:
        # CONT.0: nunca devolver fechas literales que pueden estar caducadas.
        # Si el calendario fiscal no se puede cargar, marcar la respuesta como
        # data_stale y delegar la consulta al usuario en sede AEAT.
        logger.warning("Error obteniendo vencimientos fiscales: %s", e)
        return (
            "⚠️ No se ha podido cargar el calendario fiscal AEAT en este momento "
            "(servicio temporalmente no disponible). "
            "Para evitar mostrarte fechas potencialmente desactualizadas, consulta "
            "directamente https://sede.agenciatributaria.gob.es/Sede/calendario-contribuyente.html "
            "o reintenta esta consulta en unos minutos."
        )

    if not vencimientos:
        return f"No hay vencimientos fiscales en los próximos {days_ahead} días."

    llm = get_llm(temperature=0.1, format_output="json")
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
async def check_boe_news(tenant_id: str | None = None) -> str:
    """
    Consulta las últimas novedades del BOE relevantes para PYMEs y autónomos.
    Resume el impacto y acciones recomendadas.

    Args:
        tenant_id: aceptado por consistencia con otras tools; el BOE es
            público nacional y no se filtra por tenant.
    """
    _ = tenant_id  # accepted but unused: BOE is national, same for all tenants
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

    llm = get_llm(temperature=0.1, format_output="json")
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
    - Plazo presentación Modelo 303 (IVA trimestral): 20 días tras fin de trimestre.
      El 4T es excepción: del 1 al 30 de enero del año siguiente.
    - Modelo 130 (IRPF fraccionado Estimación Directa): mismos plazos que Modelo 303
      (incluido el 4T hasta el 30 de enero).
    - Modelo 111 (Retenciones IRPF): trimestral, 20 primeros días del mes siguiente
      al trimestre. OJO: el 4T vence el 20 de enero (NO el 30 como el 303/130).
    - Factura electrónica obligatoria B2B (Ley Crea y Crece): desarrollada por el
      Real Decreto 238/2026 (BOE 31-mar-2026). El calendario arranca el 1-oct-2026;
      la obligación entra en vigor 1 año después para quienes facturen >8M€/año
      (en torno a oct-2027) y 2 años después para el resto de empresas y autónomos
      (en torno a oct-2028). Formato europeo EN16931.
    - Umbral operaciones con terceros Modelo 347: 3.005,06€ anuales.
    - Retención general profesionales: 15% (7% primeros años de actividad).
    - Autónomos en módulos: no presentan Modelo 130 sino Modelo 131.
    """


async def _search_tenant_docs(tenant_id: str, question: str) -> str:
    """Busca fragmentos relevantes en los documentos del tenant via RAG. Devuelve texto o vacío."""
    from app.agents.agent_tools.semantic_search import (
        cosine_topk,
        is_missing_table_or_extension,
    )

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
            try:
                scored = await cosine_topk(
                    db,
                    tenant_id=tenant_id,
                    query_vector=query_vector,
                    top_k=3,
                    jurisdiction=jurisdiction,
                )
            except Exception as ve:
                if is_missing_table_or_extension(ve):
                    return ""
                raise
            fragments = [m for m, _dist in scored]
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

    llm = get_llm(temperature=0.1)
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


@tool
async def check_quarter_preventive(tenant_id: str, quarter: int, year: int) -> str:
    """Asistente fiscal preventivo: detecta riesgos antes de cerrar el 303.

    Cruza facturas emitidas y recibidas del trimestre con el simulador y
    devuelve hallazgos accionables (NIF de proveedor faltante, facturas
    descuadradas, drafts olvidados, Verifactu sin registro, etc.).

    Args:
        tenant_id: UUID del tenant.
        quarter: trimestre 1-4.
        year: año del periodo (ej. 2026).
    """
    from app.services.aeat.preventive_check import check_quarter

    try:
        tid = uuid.UUID(tenant_id)
    except (TypeError, ValueError):
        return "FAIL: tenant_id no es UUID válido"
    if quarter not in (1, 2, 3, 4):
        return f"FAIL: trimestre inválido ({quarter}). Usa 1, 2, 3 o 4."

    async with AsyncSessionLocal() as db:
        findings = await check_quarter(db, tid, quarter, int(year))

    if not findings:
        return (
            f"Sin riesgos detectados para {quarter}T {year}. El trimestre "
            f"parece listo para presentar el 303."
        )

    lines = [f"Hallazgos preventivos {quarter}T {year} ({len(findings)}):", ""]
    for f in findings:
        icon = {"high": "🔴", "medium": "🟡", "low": "🔵"}.get(f.severity, "•")
        lines.append(f"{icon} [{f.code}] {f.message}")
        lines.append(f"   → {f.suggested_action}")
        if f.source_invoice_ids:
            preview = ", ".join(f.source_invoice_ids[:3])
            more = f" (+{len(f.source_invoice_ids) - 3} más)" if len(f.source_invoice_ids) > 3 else ""
            lines.append(f"   Facturas: {preview}{more}")
        lines.append("")
    return "\n".join(lines).rstrip()


tools = [
    check_fiscal_deadlines,
    check_boe_news,
    fiscal_query,
    check_quarter_preventive,
    create_document,
    list_tenant_documents,
    get_document_content,
    get_tenant_knowledge,
    upsert_tenant_knowledge,
    create_pdf_report,
    create_pdf_text_report,
]


# Defensa multi-tenant: envolver tools para forzar tenant_id del ContextVar
from app.agents.tenant_context import isolated as _isolated

tools = _isolated(tools)
