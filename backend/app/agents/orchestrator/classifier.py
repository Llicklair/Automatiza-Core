"""
Clasificador de intenciones del orquestador.
Incluye clasificación por LLM (semántica) y fallback por palabras clave.

Cache de clasificaciones
------------------------
Cada (tenant_id, intent normalizado) se memoiza en el `llm_cache` con clave
``classify:<intent_normalizado>`` y TTL configurable vía la variable de entorno
``CLASSIFY_CACHE_TTL_SECONDS`` (settings.CLASSIFY_CACHE_TTL_SECONDS, default
86400s = 24h). Esto evita recalcular la clasificación para intents recurrentes
("crea factura …", "qué tal va …") y elimina la llamada al LLM en el caso
común.

Trade-off: si modificas `_KEYWORD_MAP` o `_STRONG_KEYWORDS` y un tenant ya
tiene clasificaciones cacheadas, seguirá viendo el dominio antiguo hasta que
expire el TTL. En desarrollo conviene bajar la variable de entorno
(``CLASSIFY_CACHE_TTL_SECONDS=60``) o invalidar el cache en caliente con
``DELETE /api/v1/admin/llm-cache`` (requiere rol admin), que purga todas las
entradas con prefijo ``classify:`` para todos los tenants.
"""

import logging

from app.agents.orchestrator.classifier_data import (
    _CHITCHAT_TOKENS,
    _KEYWORD_MAP,
    _MULTI_STEP_CONNECTORS,
    _RE_AMOUNT,
    _RE_DATE,
    _RE_EMAIL,
    _RE_MONTH,
    _RE_NIF,
    _RE_NUMBER,
    _RE_QUARTER,
    _RE_WHITESPACE,
    _STRONG_KEYWORDS,
)
from app.agents.orchestrator.state import (
    VALID_DOMAINS,
    OrchestratorState,
    TaskStatus,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


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


def _strong_keyword_match(intent_lower: str) -> str | None:
    """Devuelve el dominio si algún strong keyword matchea, None si no."""
    for domain, keywords in _STRONG_KEYWORDS.items():
        for kw in keywords:
            if kw in intent_lower:
                return domain
    return None


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
        # Strong matchea un dominio pero hay conector multi-step y los keywords
        # no detectaron el segundo dominio (p.ej. "manda recordatorios por email"
        # no matchea ninguna keyword del map email). Delegar al LLM para que
        # decida si descomponer — evita resolver con un dominio único que pierde
        # el resto de acciones encadenadas.
        if _has_multi_step_connector(intent_lower):
            return "unknown"
        return strong

    if scores:
        # Multi-step: dos o más dominios distintos + conector de secuencia → coordinator
        if len(scores) >= 2 and _has_multi_step_connector(intent_lower):
            return "coordinator"

        # Mismo razonamiento que en la rama strong: conector multi-step explícito
        # con un solo dominio detectado → delegar al LLM por si hay acciones
        # encadenadas que las keywords no capturaron.
        if _has_multi_step_connector(intent_lower):
            return "unknown"

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


def _meets_employee_contract(emp) -> bool:
    """Un AIEmployee custom 'de verdad' aporta >=2 de las 4 capacidades del contrato
    (scope, memoria, conocimiento, workflows). Si aporta 0-1 es un 'Perfil' (solo
    tono/expertise) y NO debe interceptar el routing de un dominio builtin por una
    mención incidental de su nombre/rol: eso dispara un dispatch custom lento
    (timeout 180s) sin valor añadido. Ver tasks/lessons.md."""
    caps = sum((
        emp.scope is not None,
        bool(getattr(emp, "memory_enabled", False)),
        bool(getattr(emp, "knowledge_enabled", False)),
        emp.workflows is not None,
    ))
    return caps >= 2


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
                    AIEmployee.is_builtin.is_(False),
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
                # Solo intercepta si es un empleado "de verdad" (>=2 capacidades).
                # Un Perfil (0-1) mencionado de pasada NO debe secuestrar el dominio
                # builtin ni disparar un dispatch custom lento. Ver lessons.md.
                if not _meets_employee_contract(emp):
                    logger.info(
                        "[CLASSIFY] custom '%s' mencionado pero es Perfil (sin capacidades) → no intercepta routing",
                        emp.name,
                    )
                    break  # pasar al siguiente empleado
                metadata["addressed_employee_id"] = str(emp.id)
                logger.info(
                    "[CLASSIFY] empleado custom resuelto por mención '%s': %s (%s)",
                    tok, emp.name, emp.id,
                )
                return metadata

    return None


# TTL del cache de clasificaciones. Configurable vía settings.CLASSIFY_CACHE_TTL_SECONDS
# (env var CLASSIFY_CACHE_TTL_SECONDS). Default 86400s (24h). Ver docstring del módulo
# para detalles y endpoint de invalidación.
def _classify_cache_ttl() -> int:
    return settings.CLASSIFY_CACHE_TTL_SECONDS


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

    # ── Paso 0a: ¿La tarea va dirigida a un AIEmployee BUILTIN específico? ───
    # El usuario hizo /instruct con employee_id apuntando a un builtin (Ana,
    # Carlos, Patricia, etc.). Respetar SIEMPRE su domain — no clasificar ni
    # descomponer. Sin esto, prompts atómicos como "Aprueba nóminas"
    # acababan descompuestos en hr + custom + custom + summary (bug 5A).
    metadata = state.get("additional_metadata") or {}
    addressed_id = metadata.get("addressed_employee_id")
    if addressed_id:
        try:
            from uuid import UUID

            from sqlalchemy import select

            from app.db.base import AsyncSessionLocal
            from app.db.models.ai_employees import AIEmployee

            async with AsyncSessionLocal() as db:
                _r = await db.execute(
                    select(AIEmployee).where(AIEmployee.id == UUID(addressed_id))
                )
                _emp = _r.scalar_one_or_none()
            if _emp and _emp.is_builtin and _emp.domain in VALID_DOMAINS:
                logger.info(
                    "[CLASSIFY] builtin direccionado: %s (domain=%s) → respetar",
                    _emp.name, _emp.domain,
                )
                return {
                    **state,
                    "classified_domain": str(_emp.domain),
                    "status": TaskStatus.PLANNING,
                    "iteration_count": state.get("iteration_count", 0) + 1,
                }
        except Exception as _e:
            logger.debug("[CLASSIFY] lookup de addressed builtin falló: %s", _e)

    # ── Paso 0b: ¿La tarea va dirigida a un AIEmployee custom? ────────────────
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
            tenant_id, cache_key, domain, ttl_override=_classify_cache_ttl()
        )
    except Exception as e:
        logger.debug("No se pudo cachear classification: %s", e)

    return {
        **state,
        "classified_domain": domain,
        "status": TaskStatus.PLANNING,
        "iteration_count": state.get("iteration_count", 0) + 1,
    }
