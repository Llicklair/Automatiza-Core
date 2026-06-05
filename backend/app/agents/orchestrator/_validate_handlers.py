"""Node handlers: validate_node."""

import asyncio
import logging

from app.agents.orchestrator.state import VALID_DOMAINS, OrchestratorState, TaskStatus
from app.services.llm_cache import llm_cache

logger = logging.getLogger(__name__)


# Keyword → dominio. Si el planner LLM devuelve plan vacío (prompt complejo,
# json mal formado, modelo confuso) caemos a este clasificador determinista
# para asignar al menos un agente y dar una respuesta al usuario en lugar
# de marcar la tarea como FAILED.
_DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "billing": ("factura", "albaran", "albarán", "cobro", "venta", "presupuesto", "proforma"),
    "hr": ("nomina", "nómina", "empleado", "sueldo", "rrhh", "contrato laboral", "plantilla"),
    "banking": ("banco", "saldo", "transaccion", "transacción", "concilia", "movimiento bancario"),
    "accounting": ("asiento", "contabilidad", "libro mayor", "p&g", "perdida", "pérdida", "cuenta 4"),
    "compliance": ("fiscal", "iva", "modelo 303", "modelo 111", "modelo 200", "boe", "trimestre"),
    "documents": ("documento", "escanear", "archivo", "clasificar", "carpeta", "buzón", "buzon"),
    "crm": ("oportunidad", "lead", "comercial", "pipeline", "cliente nuevo"),
    "email": ("correo", "email", "enviar mensaje", "recordatorio"),
    "excel": ("excel", "hoja de calculo", "hoja de cálculo", "exportar", "xlsx"),
    "rag": ("consulta interna", "knowledge base", "politica interna", "política interna"),
    "recruitment": ("cv", "candidato", "candidata", "posicion abierta", "posición abierta"),
    "marketing": ("campaña", "campana", "catalogo", "catálogo de productos"),
}


def _heuristic_classify(intent: str) -> str:
    """Clasificador por keyword count. Devuelve el dominio con más coincidencias."""
    text = (intent or "").lower()
    scores = {d: sum(1 for kw in kws if kw in text) for d, kws in _DOMAIN_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "chat"


# Frases referenciales que aluden a un contexto previo no especificado. El
# Coordinador tendía a inventarse un plan y EJECUTARLO ante estas instrucciones
# (causa raíz C del smoke). Solo se marcan como ambiguas si además la
# instrucción no aporta nada concreto (ni dominio reconocible ni cifras), para
# no bloquear instrucciones válidas tipo «crea la factura de 500€ como siempre».
_VAGUE_PHRASES: tuple[str, ...] = (
    "lo de siempre",
    "como siempre",
    "lo habitual",
    "lo de antes",
    "lo de costumbre",
    "lo mismo de siempre",
    "lo típico",
    "lo tipico",
    "ya sabes",
    "como el otro día",
    "como el otro dia",
)


def needs_clarification(intent: str) -> tuple[bool, str]:
    """Detecta instrucciones ambiguas que NO deben ejecutarse a ciegas.

    Determinista y conservador: marca ambigüedad solo si hay una frase vaga
    («lo de siempre»…) Y la instrucción carece de contenido concreto (sin
    dominio reconocible ni cifras). Devuelve (ambigua, pregunta_de_aclaración).
    """
    text = (intent or "").lower().strip()
    if not text:
        return True, "No he recibido ninguna instrucción. ¿Qué quieres que haga?"
    vague = next((p for p in _VAGUE_PHRASES if p in text), None)
    if not vague:
        return False, ""
    has_domain = any(kw in text for kws in _DOMAIN_KEYWORDS.values() for kw in kws)
    has_number = any(c.isdigit() for c in text)
    if has_domain or has_number:
        return False, ""
    return (
        True,
        f"Tu instrucción es ambigua («{vague}»): no sé a qué operación concreta te "
        "refieres. Dime qué quieres hacer y sobre qué (p. ej. «crea una factura de "
        "500€ a Acme»). Por seguridad no ejecuto nada hasta tenerlo claro.",
    )


async def validate_node(state: OrchestratorState) -> OrchestratorState:
    """
    Validación determinista pre-ejecución.
    Verifica que el plan es ejecutable antes de invocar ningún agente o LLM.
    """
    # Guarda de ambigüedad: ante una instrucción referencial sin nada concreto
    # («haz lo de siempre con Acme»), pedir aclaración en vez de ejecutar un
    # plan inventado (causa raíz C del smoke 2026-06-03).
    ambiguous, question = needs_clarification(state.get("user_intent", ""))
    if ambiguous:
        logger.info(
            "[VALIDATE] Intención ambigua → se pide aclaración en vez de ejecutar: %s",
            (state.get("user_intent") or "")[:120],
        )
        # Marca de aclaración: no es un error real (no se ejecutó nada), sino una
        # petición de concreción. El frontend la usa para mostrarla como mensaje
        # normal en vez de "Error: …".
        meta = dict(state.get("additional_metadata") or {})
        meta["clarification"] = True
        return {
            **state,
            "status": TaskStatus.FAILED,
            "error_message": question,
            "additional_metadata": meta,
        }

    plan = state.get("plan", [])
    if not plan:
        # Fallback heurístico: el LLM no pudo descomponer la tarea (prompt
        # complejo o formato roto). En lugar de fallar, clasificamos por
        # keywords y delegamos a un único agente.
        intent = state.get("user_intent", "")
        domain = _heuristic_classify(intent)
        if domain in VALID_DOMAINS:
            logger.warning(
                "[VALIDATE] Plan LLM vacío. Fallback heurístico → agente '%s' para intent: %s",
                domain,
                intent[:120],
            )
            return {
                **state,
                "plan": [
                    {
                        "id": "step_1",
                        "agent": domain,
                        "action": "process",
                        "params": {"intent": intent},
                        "depends_on": [],
                        "status": "pending",
                    }
                ],
                "status": TaskStatus.EXECUTING,
                "iteration_count": state["iteration_count"] + 1,
            }
        return {
            **state,
            "status": TaskStatus.FAILED,
            "error_message": "El plan está vacío tras la fase de planificación",
        }

    # Fail fast: agentes inválidos no deben llegar a dispatch
    invalid = [
        f"{s['id']}={s.get('agent')!r}"
        for s in plan
        if s.get("agent") not in VALID_DOMAINS and s.get("agent") != "node_engine"
    ]
    # Pasos con agent='custom' necesitan resolver a un AIEmployee concreto.
    # Aceptamos: employee_id en los params del paso o addressed_employee_id en
    # el metadata global del state. Si no hay ninguno, falla pronto con un
    # mensaje claro en lugar de degenerarse en el dispatcher.
    addressed = (state.get("additional_metadata") or {}).get("addressed_employee_id")
    custom_unresolved = [
        s["id"]
        for s in plan
        if s.get("agent") == "custom"
        and not s.get("params", {}).get("employee_id")
        and not addressed
    ]
    if custom_unresolved:
        return {
            **state,
            "status": TaskStatus.FAILED,
            "error_message": (
                f"Pasos con agent='custom' sin employee_id: {custom_unresolved}. "
                "El planner debe especificar employee_id o el classifier debe resolver "
                "addressed_employee_id desde la mención del usuario."
            ),
        }
    if invalid:
        # Invalidar cache envenenado para que el próximo intento regenere el plan
        try:
            _tenant_id = state.get("tenant_id", "")
            _cache_key = f"plan:{state['user_intent']}"
            asyncio.create_task(llm_cache.invalidate(_tenant_id, _cache_key))
        except Exception as _e:
            logger.warning("Error invalidando caché de plan envenenado: %s", _e)
        return {
            **state,
            "status": TaskStatus.FAILED,
            "error_message": f"Plan contiene pasos con agente no reconocido: {invalid}",
        }

    return {
        **state,
        "status": TaskStatus.EXECUTING,
        "iteration_count": state["iteration_count"] + 1,
    }
