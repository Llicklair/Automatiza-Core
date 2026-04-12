"""
Clasificador de intenciones del orquestador.
Incluye clasificación por LLM (semántica) y fallback por palabras clave.
"""

import logging

from app.agents.orchestrator.state import (
    VALID_DOMAINS,
    OrchestratorState,
    TaskStatus,
)

logger = logging.getLogger(__name__)


# Reglas de palabras clave — usadas como fallback rápido si el LLM falla
_KEYWORD_MAP: dict[str, list[str]] = {
    "billing": [
        "factura",
        "facturar",
        "cobro",
        "pago",
        "cliente",
        "iva",
        "presupuesto",
        "albarán",
        "emisión",
    ],
    "documents": [
        "contrato",
        "documento",
        "archivo",
        "pdf",
        "extracto",
        "subir",
        "analizar",
        "escanear",
    ],
    "compliance": [
        "modelo",
        "hacienda",
        "aeat",
        "303",
        "130",
        "111",
        "200",
        "impuesto",
        "declaración",
        "trimestral",
    ],
    "hr": [
        "nómina",
        "nóminas",
        "empleado",
        "trabajo",
        "laboral",
        "vacaciones",
        "baja",
        "alta",
        "trabajador",
        "salario",
    ],
    "crm": [
        "venta",
        "oportunidad",
        "lead",
        "cliente potencial",
        "presupuestar",
        "reunión comercial",
        "embudo",
        "trato",
        "ganada",
    ],
    "banking": [
        "saldo",
        "balance",
        "cuenta",
        "cuentas",
        "banco",
        "transacción",
        "movimiento",
        "transferencia",
        "informe bancario",
        "iban",
        "psd2",
        "extracto bancario",
    ],
    "rag": [
        "pregunta",
        "duda",
        "consultar documento",
        "qué dice el contrato",
        "qué significa",
        "resumen documento",
    ],
    "excel": ["excel", "csv", "cruzar", "tabla", "hoja de cálculo", "datos", "columnas"],
    "email": [
        "correo",
        "email",
        "bandeja de entrada",
        "buzón",
        "inbox",
        "enviar mensaje",
        "responder correo",
    ],
    "coordinator": [
        "coordinar",
        "complejo",
        "varios agentes",
        "múltiple",
        "todos los agentes",
        "combina",
        "cruza",
    ],
    "workflow": [
        "automatización",
        "regla",
        "cada vez que",
        "programar",
        "automático",
        "workflow",
        "automatizar",
        "repetir",
    ],
    "recruitment": [
        "reclutamiento",
        "candidato",
        "cv",
        "currículum",
        "curriculum",
        "puesto abierto",
        "selección de personal",
        "contratar",
        "vacante",
        "entrevista",
        "recruiting",
        "shortlist",
    ],
    "marketing": [
        "marketing",
        "contenido",
        "redes sociales",
        "instagram",
        "facebook",
        "linkedin",
        "publicación",
        "post",
        "hashtag",
        "plan de contenidos",
        "campaña",
        "social media",
        "community manager",
    ],
    "report": [
        "informe mensual",
        "snapshot",
        "resumen del mes",
        "estado de la empresa",
        "informe completo",
        "informe empresarial",
        "análisis mensual",
        "cierre mensual",
        "genera el informe",
        "informe de gestión",
        "resumen mensual",
    ],
    "chat": [
        "qué es",
        "cómo funciona",
        "explica",
        "diferencia entre",
        "qué significa",
        "ayuda",
        "terminó",
        "ha terminado",
        "estado de la tarea",
        "cómo va",
        "qué tal va",
        "puedes",
        "sabes",
        "entiendes",
        "gracias",
        "hola",
        "buenas",
    ],
}

from app.prompts import load_prompt

_CLASSIFY_SYSTEM = load_prompt("classifier")


def _is_question(text: str) -> bool:
    """Detecta si el texto es una pregunta general (no una acción)."""
    t = text.strip()
    if t.startswith("¿") or t.endswith("?"):
        # Excluir preguntas que son acciones implícitas: "¿puedes crear...", "¿me generas..."
        action_verbs = [
            "crea",
            "genera",
            "envía",
            "enviar",
            "haz",
            "hacer",
            "registra",
            "sube",
            "subir",
        ]
        return not any(v in t.lower() for v in action_verbs)
    question_starts = [
        "cuántas",
        "cuántos",
        "cuánto",
        "cuándo",
        "dónde",
        "cómo",
        "qué es",
        "qué son",
        "hay ",
        "tiene ",
        "están ",
        "está ",
        "se ejecutó",
        "terminó",
        "ha terminado",
        "funcionó",
        "falló",
        "explica",
        "diferencia",
        "ayuda",
        "hola",
        "buenas",
        "gracias",
    ]
    return any(t.lower().startswith(q) for q in question_starts)


def _keyword_classify(intent_lower: str) -> str:
    """Clasificación determinista por palabras clave — fallback rápido."""
    # Primero: buscar coincidencia con dominios especializados
    for domain, keywords in _KEYWORD_MAP.items():
        if domain == "chat":
            continue
        if any(kw in intent_lower for kw in keywords):
            return domain
    # Solo si NO hay dominio detectado: preguntas generales van a chat
    if _is_question(intent_lower):
        return "chat"
    return "unknown"


async def classify_node(state: OrchestratorState) -> OrchestratorState:
    """
    Clasifica la intención del usuario en un dominio.
    Si el domain ya viene definido (desde la BD/API), se usa directamente.
    Estrategia fallback: LLM (comprensión semántica) → palabras clave.
    """
    # ── Atajo: si el domain ya está definido y es válido, no reclasificar ────
    existing_domain = state.get("classified_domain")
    if existing_domain and existing_domain in VALID_DOMAINS:
        return {
            **state,
            "classified_domain": existing_domain,
            "status": TaskStatus.PLANNING,
            "iteration_count": state.get("iteration_count", 0) + 1,
        }

    intent = state["user_intent"]
    intent_lower = intent.lower()

    # ── Paso 1: Palabras clave — rápido y sin coste ──────────────────────────
    domain = _keyword_classify(intent_lower)

    # ── Paso 2: LLM semántico solo si keywords no resolvieron ────────────────
    if domain == "unknown":
        tenant_id = state.get("tenant_id", "")
        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            from app.core.llm_factory import get_llm
            from app.services.llm_cache import llm_cache

            cache_key_intent = f"classify:{intent_lower}"
            cached = await llm_cache.get(tenant_id, cache_key_intent)
            if cached and cached in VALID_DOMAINS:
                domain = cached
            else:
                llm = get_llm(temperature=0)
                import asyncio as _asyncio

                response = await _asyncio.wait_for(
                    llm.ainvoke(
                        [
                            SystemMessage(content=_CLASSIFY_SYSTEM),
                            HumanMessage(content=intent),
                        ]
                    ),
                    timeout=30,
                )
                raw = response.content.strip().lower().split()[0] if response.content else ""
                if raw in VALID_DOMAINS:
                    domain = raw
                    await llm_cache.set(tenant_id, cache_key_intent, domain, ttl_override=7200)
        except Exception as e:
            logger.debug("Fallo en clasificación LLM: %s", e)

    return {
        **state,
        "classified_domain": domain,
        "status": TaskStatus.PLANNING,
        "iteration_count": state.get("iteration_count", 0) + 1,
    }
