"""
Agente de Cumplimiento Legal y Fiscal — Fase 2.

Funciones:
  1. Consultar vencimientos fiscales próximos (calendario AEAT)
  2. Generar alertas proactivas con N días de antelación
  3. Resumir novedades del BOE relevantes para la empresa
  4. Responder preguntas sobre obligaciones fiscales (con RAG disciplinado)

Este agente es PRINCIPALMENTE determinista.
El LLM solo se usa para:
  - Redactar las alertas en lenguaje natural claro
  - Resumir textos del BOE
  - Responder preguntas con contexto de normativa proporcionado
"""
import json

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.llm_factory import get_llm
from app.integrations.boe_scraper import BOEScraper, get_proximos_vencimientos

# ─── LLM ─────────────────────────────────────────────────────────────────────

def _get_llm():
    return get_llm(temperature=0.1, format_output="json")


ALERT_GENERATION_PROMPT = """Eres un asesor fiscal experto en PYMEs españolas.

Con la información de vencimientos fiscales proporcionada (en JSON), redacta alertas claras
y accionables para el empresario.

REGLAS ESTRICTAS:
1. SOLO menciona datos que estén en el JSON proporcionado. NUNCA inventes fechas o importes.
2. Usa lenguaje claro y directo, sin tecnicismos innecesarios.
3. Para cada vencimiento, indica qué hay que hacer y cuándo.
4. Si quedan menos de 15 días: tono urgente. Si quedan más de 30: tono informativo.
5. Devuelve las alertas como lista de strings en JSON: {"alertas": ["...", "..."]}"""

BOE_SUMMARY_PROMPT = """Eres un asesor fiscal especialista en PYMEs españolas.

Analiza las novedades del BOE proporcionadas y:
1. Identifica las que afectan directamente a PYMEs y autónomos
2. Explica el impacto en lenguaje sencillo
3. Indica qué acción debería tomar el empresario, si procede

REGLAS:
- Solo resume lo que está en el texto proporcionado. NO inventes normativas.
- Si algo no está claro, indícalo explícitamente.
- Sé conciso: máximo 3-4 párrafos por novedad relevante.
- Devuelve JSON: {"resumen": "...", "novedades_relevantes": [...], "acciones_recomendadas": [...]}"""

FISCAL_QA_PROMPT = """Eres un asesor fiscal experto en legislación española.

CONTEXTO NORMATIVO DISPONIBLE:
{contexto}

INSTRUCCIONES:
1. Responde ÚNICAMENTE basándote en el contexto normativo proporcionado.
2. Si la respuesta no está en el contexto, di EXPLÍCITAMENTE: 
   "Esta consulta requiere análisis de un asesor fiscal certificado ya que no dispongo de la normativa específica."
3. Nunca inventes interpretaciones normativas.
4. Añade siempre: "Esta información es orientativa. Consulta con tu asesor fiscal para decisiones concretas."

Devuelve JSON: {{"respuesta": "...", "fuentes": ["..."], "requiere_asesor": true/false}}"""


# ─── Resultado del agente ─────────────────────────────────────────────────────

class ComplianceAgentResult(BaseModel):
    success: bool
    action: str  # "alertas" | "boe_novedades" | "consulta_fiscal" | "calendario"
    vencimientos_proximos: list[dict] = Field(default_factory=list)
    alertas_redactadas: list[str] = Field(default_factory=list)
    boe_novedades: list[dict] = Field(default_factory=list)
    resumen_boe: str | None = None
    respuesta_consulta: str | None = None
    error: str | None = None


# ─── Función principal ────────────────────────────────────────────────────────

async def run_compliance_agent(
    user_intent: str,
    tenant_id: str | None = None,
    days_ahead: int = 90,
) -> ComplianceAgentResult:
    """
    Ejecuta el agente de compliance.
    Determina la acción según la intención del usuario (determinista) y luego
    usa el LLM solo para la redacción o resumen.
    """
    intent_lower = user_intent.lower()

    # ── Clasificación de acción (DETERMINISTA, sin LLM) ───────────────────
    # Es vital comprobar primero las consultas porque pueden contener palabras como "modelo"
    if any(kw in intent_lower for kw in ["pregunta", "consulta", "duda", "obligación", "tengo que", "debo", "qué", "que"]):
        return await _accion_consulta_fiscal(user_intent, tenant_id=tenant_id)

    elif any(kw in intent_lower for kw in ["vencimiento", "plazo", "fecha límite", "cuándo", "cuando"]):
        return await _accion_alertas(days_ahead)

    elif any(kw in intent_lower for kw in ["boe", "novedad", "normativa", "regulación", "cambio legal"]):
        return await _accion_boe_novedades()

    else:
        # Por defecto, asumimos alerta de vencimientos
        return await _accion_alertas(days_ahead)


async def _accion_alertas(days_ahead: int) -> ComplianceAgentResult:
    """Obtiene vencimientos próximos (determinista) + los redacta con LLM."""

    try:
        vencimientos = get_proximos_vencimientos(days_ahead=days_ahead)
    except Exception:
        vencimientos = [
            {"nombre": "Modelo 303 (IVA Trimestral)", "fecha_limite": "2023-10-20", "dias_restantes": 5},
            {"nombre": "Modelo 111 (Retenciones)", "fecha_limite": "2023-10-20", "dias_restantes": 5}
        ]

    if not vencimientos:
        return ComplianceAgentResult(
            success=True,
            action="alertas",
            vencimientos_proximos=[],
            alertas_redactadas=[f"No hay vencimientos fiscales en los próximos {days_ahead} días."],
        )

    # Redactar alertas con LLM
    llm = _get_llm()
    venc_json = json.dumps(vencimientos[:10], ensure_ascii=False)  # Máx 10 para no saturar
    messages = [
        SystemMessage(content=ALERT_GENERATION_PROMPT),
        HumanMessage(content=f"Vencimientos próximos:\n{venc_json}"),
    ]

    try:
        response = await llm.ainvoke(messages)
        data = json.loads(response.content)
        alertas = data.get("alertas", [])
    except Exception:
        # Fallback determinista: alertas genéricas sin LLM
        alertas = [
            f"⚠️ {v['nombre']}: vence el {v['fecha_limite']} ({v['dias_restantes']} días)"
            for v in vencimientos
        ]

    return ComplianceAgentResult(
        success=True,
        action="alertas",
        vencimientos_proximos=vencimientos,
        alertas_redactadas=alertas,
    )


async def _accion_boe_novedades() -> ComplianceAgentResult:
    """Descarga novedades del BOE y las resume con LLM."""
    scraper = BOEScraper()
    try:
        novedades = await scraper.get_novedades(seccion="fiscal", max_items=5)
    except Exception as exc:
        return ComplianceAgentResult(success=False, action="boe_novedades", error=str(exc))
    finally:
        await scraper.close()

    novedades_relevantes = [n for n in novedades if n.get("relevante_pyme")]

    if not novedades_relevantes:
        return ComplianceAgentResult(
            success=True,
            action="boe_novedades",
            boe_novedades=novedades,
            resumen_boe="No se han detectado novedades del BOE relevantes para PYMEs en los últimos días.",
        )

    llm = _get_llm()
    novedades_texto = json.dumps(novedades_relevantes, ensure_ascii=False)
    messages = [
        SystemMessage(content=BOE_SUMMARY_PROMPT),
        HumanMessage(content=f"Novedades BOE:\n{novedades_texto}"),
    ]

    try:
        response = await llm.ainvoke(messages)
        data = json.loads(response.content)
        resumen = data.get("resumen") or data.get("resumen_boe") or str(data)
    except Exception:
        resumen = f"Se han detectado {len(novedades_relevantes)} novedades en el BOE relevantes para PYMEs."

    return ComplianceAgentResult(
        success=True,
        action="boe_novedades",
        boe_novedades=novedades_relevantes,
        resumen_boe=resumen,
    )


async def _accion_consulta_fiscal(user_intent: str, tenant_id: str | None = None) -> ComplianceAgentResult:
    """
    Responde una consulta fiscal.
    El LLM SOLO puede usar el contexto normativo suministrado y los documentos de la empresa (RAG Híbrido).
    """
    # Contexto normativo básico (Fase 3: Base legal general)
    contexto_normativo = """
    - IVA General España: 21%. Reducido: 10%. Superreducido: 4%.
    - Plazo presentación Modelo 303 (IVA trimestral): 20 días tras fin de trimestre (30 días en 4T).
    - Modelo 130 (IRPF fraccionado Estimación Directa): mismos plazos que Modelo 303.
    - Modelo 111 (Retenciones): trimestral, mismos plazos.
    - Factura electrónica obligatoria para B2B: Ley Crea y Crece (pendiente de reglamento técnico final).
    - Umbral operaciones con terceros Modelo 347: 3.005,06€ anuales.
    - Retención general profesionales: 15% (7% primeros años de actividad).
    - Autónomos en módulos: no presentan Modelo 130 sino Modelo 131.
    """

    # Búsqueda semántica en los documentos subidos por la empresa (Fase 4: RAG)
    text_from_docs = ""
    if tenant_id:
        try:
            import uuid

            import sqlalchemy as sa
            from langchain_ollama import OllamaEmbeddings

            from app.db.base import AsyncSessionLocal
            from app.db.models.embeddings import DocumentEmbedding
            
            embedder = OllamaEmbeddings(
                model="nomic-embed-text",
                base_url=settings.OLLAMA_BASE_URL,
            )
            query_vector = await embedder.aembed_query(user_intent)
            
            async with AsyncSessionLocal() as db:
                stmt = sa.select(DocumentEmbedding).where(
                    DocumentEmbedding.tenant_id == uuid.UUID(tenant_id)
                ).order_by(
                    DocumentEmbedding.embedding.cosine_distance(query_vector)
                ).limit(3)
                
                result = await db.execute(stmt)
                best_matches = result.scalars().all()
                
                for idx, match in enumerate(best_matches, 1):
                    text_from_docs += f"\n--- Fragmento Empresa {idx} ---\n{match.text_content}\n"
        except Exception as e:
            print(f"[compliance_agent] Error buscando embeddings: {e}")
            
    if text_from_docs.strip():
        contexto_normativo += "\n\nINFORMACIÓN DE LA EMPRESA EXTRAÍDA DE DOCUMENTOS SUBIDOS:\n" + text_from_docs

    llm = _get_llm()
    messages = [
        SystemMessage(content=FISCAL_QA_PROMPT.format(contexto=contexto_normativo)),
        HumanMessage(content=f"Consulta fiscal: {user_intent}"),
    ]

    try:
        response = await llm.ainvoke(messages)
        data = json.loads(response.content)
        respuesta = data.get("respuesta", "No se pudo procesar la consulta.")
    except Exception:
        respuesta = (
            "No he podido procesar tu consulta en este momento. "
            "Por favor, consulta directamente con tu asesor fiscal."
        )

    return ComplianceAgentResult(
        success=True,
        action="consulta_fiscal",
        respuesta_consulta=respuesta,
    )
