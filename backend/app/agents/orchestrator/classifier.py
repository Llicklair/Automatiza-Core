"""
Clasificador de intenciones del orquestador.
Incluye clasificación por LLM (semántica) y fallback por palabras clave.
"""

import logging
import re

from app.agents.orchestrator.state import (
    VALID_DOMAINS,
    OrchestratorState,
    TaskStatus,
)

logger = logging.getLogger(__name__)

# Patrones de normalización: tokens que NO afectan la clasificación pero rompen
# el cache hit ("crea factura 500" vs "crea factura 600" deberían ser el mismo).
_RE_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_RE_NIF = re.compile(r"\b[A-Z]?\d{7,8}[A-Z]?\b", re.IGNORECASE)
_RE_DATE = re.compile(
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b"
)
_RE_AMOUNT = re.compile(r"\b\d[\d.,]*\s*(?:€|eur|euros?|usd|\$|%)\b", re.IGNORECASE)
_RE_NUMBER = re.compile(r"\b\d+([.,]\d+)?\b")
_RE_WHITESPACE = re.compile(r"\s+")
_RE_MONTH = re.compile(
    r"\b(enero|febrero|marzo|abril|mayo|junio|julio|"
    r"agosto|septiembre|octubre|noviembre|diciembre)\b",
    re.IGNORECASE,
)
_RE_QUARTER = re.compile(r"\b[qQ][1-4]\b")


def _normalize_for_cache(text: str) -> str:
    """Normaliza el intent para maximizar hits del cache de classifier.

    Sustituye importes, fechas, NIFs, emails, números por placeholders.
    Mantiene el resto en minúsculas. Dos intents con la misma estructura pero
    valores distintos comparten cache (e.g. 'crea factura 500 EUR' y
    'crea factura 600 EUR' colapsan al mismo key).
    """
    t = text.lower().strip()
    t = _RE_EMAIL.sub("<email>", t)
    t = _RE_AMOUNT.sub("<amount>", t)
    t = _RE_DATE.sub("<date>", t)
    t = _RE_NIF.sub("<nif>", t)
    t = _RE_MONTH.sub("<month>", t)
    t = _RE_QUARTER.sub("<quarter>", t)
    t = _RE_NUMBER.sub("<num>", t)
    t = _RE_WHITESPACE.sub(" ", t).strip()
    return t


# Reglas de palabras clave — usadas como fallback rápido si el LLM falla
_KEYWORD_MAP: dict[str, list[str]] = {
    "billing": [
        "factura",
        "facturar",
        "cobro",
        "pago",
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
        "modelo 303",
        "modelo 130",
        "modelo 111",
        "modelo 200",
        "modelo 390",
        "hacienda",
        "aeat",
        "impuesto",
        "declaración trimestral",
        "declaración del iva",
    ],
    "hr": [
        "nómina",
        "nóminas",
        "empleado",
        "laboral",
        "vacaciones",
        "baja médica",
        "trabajador",
        "salario",
        "sueldo",
        "contrato laboral",
    ],
    "crm": [
        "venta",
        "oportunidad",
        "lead",
        "cliente potencial",
        "nuevo cliente",
        "alta de cliente",
        "añade un cliente",
        "registra un cliente",
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
        "qué dice",
        "qué dicen",
        "qué hay sobre",
        "qué tenemos sobre",
        "qué información",
        "qué dice nuestra",
        "según el contrato",
        "según el documento",
        "según los documentos",
        "según la política",
        "política interna",
        "consultar documento",
        "consultar la documentación",
        "preguntar a la documentación",
        "pregúntale a la documentación",
        "busca en los documentos",
        "resume el documento",
        "qué significa",
    ],
    "excel": ["excel", "csv", "cruzar", "tabla", "hoja de cálculo", "datos", "columnas"],
    "email": [
        "correo electrónico",
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
    "accounting": [
        "asiento",
        "asiento contable",
        "libro diario",
        "contabilidad",
        "cuenta contable",
        "pgc",
        "amortización",
        "balance de situación",
        "pérdidas y ganancias",
        "inmovilizado",
        "activo fijo",
        "debe",
        "haber",
        "conciliación contable",
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


_CHITCHAT_TOKENS = {
    "hola", "buenas", "buenos días", "buenas tardes", "buenas noches",
    "gracias", "ok", "vale", "qué tal", "cómo estás",
}

# Strong keywords: si alguno matchea → dominio devuelto directamente sin scoring.
# Solo poner aquí términos altamente predictivos del dominio (alta precisión, baja
# ambigüedad). Si dudas si añadir uno, NO lo añadas — déjalo en _KEYWORD_MAP.
# Orden importa: el primer match gana cuando hay strong en varios dominios.
# Pones primero los dominios más específicos / "acción primaria" frente a
# dominios "objeto/recurso" (billing puede aparecer como complemento).
_STRONG_KEYWORDS: dict[str, list[str]] = {
    # Acciones específicas primero
    "rag": [
        "qué dice", "qué dicen", "qué hay sobre", "qué tenemos sobre",
        "qué información tenemos", "según el contrato", "según el documento",
        "según los documentos", "según la política", "política interna",
        "consultar la documentación", "preguntar a la documentación",
        "pregúntale a la documentación", "busca en los documentos",
        "resume el documento",
    ],
    "compliance": ["modelo 303", "modelo 130", "modelo 111", "modelo 200",
                   "modelo 390", "aeat", "hacienda"],
    "banking": ["iban", "concilia", "concilia movimiento", "extracto bancario",
                "resumen financiero", "estado financiero", "saldo de la cuenta",
                "transferencia"],
    "email": ["envía un email", "envía email", "envía un correo", "envía correo",
              "manda un email", "manda email", "manda un correo", "responde el correo",
              "responde el email", "bandeja de entrada", "revisa el inbox"],
    "workflow": ["crea un workflow", "automatización", "workflow", "cada lunes",
                 "cada martes", "cada miércoles", "cada jueves", "cada viernes",
                 "cada día", "cada semana"],
    "documents": ["escanea", "escanear este", "sube este pdf", "sube este documento",
                  "clasifica los documentos", "clasifica el documento"],
    "recruitment": ["candidato", "currículum", "shortlist", "selección de personal",
                    "vacante", "oferta de trabajo", "publica una oferta",
                    "publicar una oferta", "puesto vacante"],
    "marketing": ["campaña de marketing", "redes sociales", "instagram", "linkedin"],
    "excel": ["excel", "csv", "hoja de cálculo"],
    "accounting": [
        "asiento contable", "libro diario", "crea un asiento", "asiento de",
        "balance de situación", "pérdidas y ganancias", "cuenta contable",
        "inmovilizado", "activo fijo", "amortización del inmovilizado",
    ],
    "report": ["informe mensual", "snapshot", "estado de la empresa", "cierre mensual"],
    # Dominios "objeto/recurso" al final (pueden aparecer como complemento de acción)
    "hr": ["nómina", "nóminas", "da de alta empleado", "alta del empleado",
           "alta de empleado"],
    "billing": ["factura", "facturas", "cobro de", "presupuesto"],
}


def _strong_keyword_match(intent_lower: str) -> str | None:
    """Devuelve el dominio si algún strong keyword matchea, None si no."""
    for domain, keywords in _STRONG_KEYWORDS.items():
        for kw in keywords:
            if kw in intent_lower:
                return domain
    return None


_MULTI_STEP_CONNECTORS = (
    " y luego ", " y después ", " y envía", " y manda",
    " y prepara", " y genera", " y crea", " y notifica", " también ",
    ", luego ", ", después ", " después de ",
)


def _has_multi_step_connector(intent_lower: str) -> bool:
    return any(c in intent_lower for c in _MULTI_STEP_CONNECTORS)


def _is_pure_chitchat(intent_lower: str) -> bool:
    """True si el intent es un saludo/cortesía sin contenido accionable."""
    stripped = intent_lower.strip("?!.¿¡ ")
    if not stripped:
        return False
    # Hasta 6 palabras y empieza por un token de chitchat
    if len(stripped.split()) > 6:
        return False
    return any(stripped.startswith(t) for t in _CHITCHAT_TOKENS)


def _keyword_classify(intent_lower: str) -> str:
    """Clasificación determinista por palabras clave usando scoring por dominio.

    Score = nº de keywords distintos del dominio que aparecen en el intent.
    Devuelve el dominio con score máximo si gana de forma clara; si hay empate
    o ningún match, devuelve 'unknown' para que el LLM decida.
    """
    # 0. Saludos puros → chat directo
    if _is_pure_chitchat(intent_lower):
        return "chat"

    # 0b. Strong keywords: una sola coincidencia → dominio resuelto…
    strong = _strong_keyword_match(intent_lower)

    # 1. Scoring de dominios especializados (chat se trata aparte)
    scores: dict[str, int] = {}
    for domain, keywords in _KEYWORD_MAP.items():
        if domain == "chat":
            continue
        n = sum(1 for kw in keywords if kw in intent_lower)
        if n:
            scores[domain] = n

    # 0c. …pero si hay strong + OTRO dominio en score + conector multi-step → coordinator.
    if strong is not None:
        other_domains = [d for d in scores if d != strong]
        if other_domains and _has_multi_step_connector(intent_lower):
            return "coordinator"
        return strong

    if scores:
        # Multi-step: dos o más dominios distintos + conector de secuencia → coordinator
        if len(scores) >= 2 and _has_multi_step_connector(intent_lower):
            return "coordinator"

        sorted_doms = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top, top_score = sorted_doms[0]
        runner_up = sorted_doms[1][1] if len(sorted_doms) > 1 else 0
        # Ganador claro: el top tiene al menos 2 matches o duplica al siguiente
        if top_score >= 2 or top_score > runner_up:
            return top
        # Empate ambiguo → dejar al LLM
        return "unknown"

    # 2. Sin matches: si parece pregunta → chat
    if _is_question(intent_lower):
        return "chat"
    return "unknown"


async def _resolve_custom_employee(state: OrchestratorState, intent_lower: str) -> dict | None:
    """Si la tarea va dirigida a un AIEmployee custom (por id en metadata o por nombre/rol
    mencionado en el texto), devuelve el dict de metadata enriquecido y enruta a 'custom'.

    Devuelve None si no hay empleado custom direccionable.
    """
    from uuid import UUID

    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    from app.db.models.ai_employees import AIEmployee

    metadata = dict(state.get("additional_metadata") or {})
    tenant_id = state.get("tenant_id")
    if not tenant_id:
        return None

    # Caso 1: el cliente ya pasó addressed_employee_id (UI con selector de empleado)
    if metadata.get("addressed_employee_id"):
        return metadata

    # Caso 2: detectar mención por nombre o rol en el texto natural
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(AIEmployee).where(
                    AIEmployee.tenant_id == UUID(tenant_id),
                    AIEmployee.domain == "custom",
                    AIEmployee.status.in_(("idle", "working", "pending_setup")),
                )
            )
            employees = result.scalars().all()
    except Exception as e:
        logger.debug("No se pudo cargar AIEmployees custom: %s", e)
        return None

    import re

    _STOPWORDS = {"de", "del", "la", "el", "los", "las", "y", "o", "para", "por"}

    def _word_tokens(text: str) -> list[str]:
        if not text:
            return []
        cleaned = re.sub(r"[()\[\]]", " ", text.lower())
        return [t for t in cleaned.split() if len(t) >= 3 and t not in _STOPWORDS]

    for emp in employees:
        tokens: set[str] = set()
        tokens.update(_word_tokens(emp.name))
        tokens.update(_word_tokens(emp.role))
        if emp.name:
            tokens.add(emp.name.lower())  # match nombre completo
        if not tokens:
            continue
        for tok in tokens:
            if re.search(r"\b" + re.escape(tok) + r"\b", intent_lower):
                metadata["addressed_employee_id"] = str(emp.id)
                logger.info(
                    "[CLASSIFY] empleado custom resuelto por mención '%s': %s (%s)",
                    tok, emp.name, emp.id,
                )
                return metadata

    return None


_CACHE_TTL_CLASSIFY = 86400  # 24 h — los patrones de clasificación no cambian a menudo


async def classify_node(state: OrchestratorState) -> OrchestratorState:
    """
    Clasifica la intención del usuario en un dominio.
    Si el domain ya viene definido (desde la BD/API), se usa directamente.
    Estrategia: cache → custom employee → keywords → LLM → fallback a chat.
    """
    from app.services.llm_cache import llm_cache

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
    tenant_id = state.get("tenant_id", "")
    cache_key = f"classify:{_normalize_for_cache(intent)}"

    # ── Paso 0: ¿La tarea va dirigida a un AIEmployee custom? ────────────────
    # No se cachea: depende del estado de AIEmployees del tenant (puede cambiar).
    custom_metadata = await _resolve_custom_employee(state, intent_lower)
    if custom_metadata is not None:
        return {
            **state,
            "classified_domain": "custom",
            "additional_metadata": custom_metadata,
            "status": TaskStatus.PLANNING,
            "iteration_count": state.get("iteration_count", 0) + 1,
        }

    # ── Paso 1: cache hit por intent normalizado ─────────────────────────────
    cached = await llm_cache.get(tenant_id, cache_key)
    if cached and cached in VALID_DOMAINS:
        logger.debug("[CLASSIFY] cache hit para '%s' → %s", cache_key, cached)
        return {
            **state,
            "classified_domain": cached,
            "status": TaskStatus.PLANNING,
            "iteration_count": state.get("iteration_count", 0) + 1,
        }

    # ── Paso 2: keywords + scoring ───────────────────────────────────────────
    domain = _keyword_classify(intent_lower)

    # ── Paso 3: LLM semántico solo si keywords no resolvieron ────────────────
    if domain == "unknown":
        try:
            import asyncio as _asyncio

            from langchain_core.messages import HumanMessage, SystemMessage

            from app.core.llm_factory import get_llm

            llm = get_llm(temperature=0)
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
        except Exception as e:
            logger.debug("Fallo en clasificación LLM: %s", e)

    # ── Paso 4: fallback a chat si no se resolvió ────────────────────────────
    if domain not in VALID_DOMAINS:
        logger.info("[CLASSIFY] sin dominio resuelto para intent='%s'; fallback a chat", intent[:80])
        domain = "chat"

    # ── Paso 5: cachear el resultado (cualquier vía: keyword o LLM) ──────────
    try:
        await llm_cache.set(
            tenant_id, cache_key, domain, ttl_override=_CACHE_TTL_CLASSIFY
        )
    except Exception as e:
        logger.debug("No se pudo cachear classification: %s", e)

    return {
        **state,
        "classified_domain": domain,
        "status": TaskStatus.PLANNING,
        "iteration_count": state.get("iteration_count", 0) + 1,
    }
