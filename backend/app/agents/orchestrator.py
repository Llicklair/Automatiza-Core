"""
Orquestador central basado en LangGraph.
Implementa el grafo de estado: Classify → Plan → Validate → Dispatch → [Agent] → Result
"""
import logging
import re
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, TypedDict

logger = logging.getLogger(__name__)

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

# ─── Estado compartido del grafo ─────────────────────────────────────────────

class TaskStatus(str, Enum):
    PENDING = "pending"
    CLASSIFYING = "classifying"
    PLANNING = "planning"
    VALIDATING = "validating"
    EXECUTING = "executing"
    AWAITING_APPROVAL = "awaiting_approval"
    DONE = "done"
    FAILED = "failed"


class SubTask(TypedDict):
    id: str
    agent: str        # billing | documents | compliance | hr
    action: str
    params: dict
    depends_on: list[str]
    status: str       # pending | done | failed


class AgentResult(TypedDict):
    subtask_id: str
    agent: str
    success: bool
    output: Any
    error: str | None


class OrchestratorState(TypedDict):
    # Identidad
    task_id: str
    tenant_id: str
    user_id: str

    # Intención
    user_intent: str
    current_intent: str | None = None  # Contexto enriquecido para el paso actual
    classified_domain: str | None

    # Planificación
    plan: list[SubTask] | None
    current_step: int

    # Ejecución
    agent_results: list[AgentResult]

    # Control de flujo
    status: TaskStatus
    requires_human_approval: bool
    approval_id: str | None
    error_message: str | None

    # Metadatos
    iteration_count: int  # Protección anti-bucle infinito
    tenant_knowledge: list[dict] = []
    additional_metadata: dict[str, Any] = None


MAX_ITERATIONS = 20  # Límite duro


# ─── Utilidad: extraer mes y año de lenguaje natural ─────────────────────────

_MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
    # abreviaturas comunes
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "jun": 6, "jul": 7,
    "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
}

def _extract_month_year(intent: str) -> tuple[int, int]:
    """Extrae (mes, año) de un texto en lenguaje natural español.

    Maneja:
    - Nombres de mes: "marzo", "enero 2025", "el pasado octubre"
    - Relativos: "mes pasado", "mes anterior", "mes que viene", "próximo mes"
    - Numérico ISO: "2026-03", "2026/03"
    - Numérico directo: "03/2026", "3/2026", "mes 3"
    - Sin contexto: devuelve mes actual
    """
    now = datetime.now()
    text = intent.lower()

    # Relativos primero
    if re.search(r"mes\s+(pasado|anterior)", text):
        d = (now.replace(day=1) - timedelta(days=1))
        return d.month, d.year
    if re.search(r"(próximo|siguiente|que\s+viene)\s+mes|mes\s+(próximo|siguiente|que\s+viene)", text):
        d = (now.replace(day=28) + timedelta(days=4))
        return d.month, d.year

    # Formato ISO: 2026-03 o 2026/03
    m = re.search(r"\b(20\d{2})[/-](\d{1,2})\b", text)
    if m:
        return int(m.group(2)), int(m.group(1))

    # Formato DD/MM/YYYY o MM/YYYY
    m = re.search(r"\b(\d{1,2})[/-](20\d{2})\b", text)
    if m:
        return int(m.group(1)), int(m.group(2))

    # Nombre de mes (con año opcional)
    for nombre, num in _MESES_ES.items():
        if re.search(rf"\b{nombre}\b", text):
            year_m = re.search(r"\b(20\d{2})\b", text)
            year = int(year_m.group(1)) if year_m else now.year
            return num, year

    # "mes N" numérico
    m = re.search(r"\bmes\s+(\d{1,2})\b", text)
    if m:
        month = int(m.group(1))
        if 1 <= month <= 12:
            year_m = re.search(r"\b(20\d{2})\b", text)
            year = int(year_m.group(1)) if year_m else now.year
            return month, year

    # Año solo → mes actual de ese año
    m = re.search(r"\b(20\d{2})\b", text)
    if m:
        return now.month, int(m.group(1))

    # Por defecto: mes actual
    return now.month, now.year


# ─── Dominios disponibles ─────────────────────────────────────────────────────

VALID_DOMAINS = {"billing", "documents", "compliance", "hr", "banking", "rag", "crm", "excel", "email", "coordinator", "workflow", "skill"}

# Reglas de palabras clave — usadas como fallback rápido si el LLM falla
_KEYWORD_MAP: dict[str, list[str]] = {
    "billing":    ["factura", "facturar", "cobro", "pago", "cliente", "iva", "presupuesto", "albarán", "emisión"],
    "documents":  ["contrato", "documento", "archivo", "pdf", "extracto", "subir", "analizar", "escanear"],
    "compliance": ["modelo", "hacienda", "aeat", "303", "130", "111", "200", "impuesto", "declaración", "trimestral"],
    "hr":         ["nómina", "nóminas", "empleado", "trabajo", "laboral", "vacaciones", "baja", "alta", "trabajador", "salario"],
    "crm":        ["venta", "oportunidad", "lead", "cliente potencial", "presupuestar", "reunión comercial", "embudo", "trato", "ganada"],
    "banking":    ["saldo", "balance", "cuenta", "cuentas", "banco", "transacción", "movimiento",
                   "transferencia", "informe bancario", "iban", "psd2", "extracto bancario"],
    "rag":        ["pregunta", "duda", "consultar documento", "qué dice el contrato", "qué significa", "resumen documento"],
    "excel":      ["excel", "csv", "cruzar", "tabla", "hoja de cálculo", "datos", "columnas"],
    "email":      ["correo", "email", "bandeja de entrada", "buzón", "inbox", "enviar mensaje", "responder correo"],
    "coordinator": ["coordinar", "complejo", "varios agentes", "múltiple", "todos los agentes", "combina", "cruza"],
    "workflow": ["automatización", "regla", "cada vez que", "programar", "automático", "workflow", "automatizar", "repetir"],
    "report": ["informe mensual", "snapshot", "resumen del mes", "estado de la empresa", "informe completo", "informe empresarial",
               "análisis mensual", "cierre mensual", "genera el informe", "informe de gestión", "resumen mensual"],
}

_CLASSIFY_SYSTEM = """\
Eres un clasificador de intenciones para una plataforma de automatización empresarial española.
Tu única tarea es leer el texto del usuario y responder con UN SOLO valor del siguiente conjunto:
  billing | documents | compliance | hr | banking | rag | excel | email | workflow | coordinator | report | unknown

Definiciones:
- billing: crear, enviar o consultar facturas, presupuestos, albaranes o cobros a clientes.
- documents: subir, analizar, clasificar o gestionar documentos, PDFs, contratos.
- compliance: modelos fiscales (303, 130, 111, 200), declaraciones AEAT, hacienda.
- hr: nóminas, empleados, contratos laborales, vacaciones, bajas médicas, adelantos.
- workflow: crear, modificar o eliminar automatizaciones, reglas recurrentes, tareas programadas.
- coordinator: tareas complejas que requieren múltiples pasos o agentes.
- crm: ventas, mover leads, nuevas oportunidades de negocio, embudo de clientes, tratos.
- banking: saldos bancarios, transacciones, movimientos, cuentas, informes financieros.
- rag: buscar información o responder preguntas sobre el contenido de documentos archivados.
- excel: manipular datos, cruzar archivos excel o csv, generar informes tabulares.
- email: revisar bandeja de entrada, leer o responder y procesar correos electrónicos.
- report: generar informe mensual, resumen del estado de la empresa, análisis mensual completo, cierre mensual, snapshot empresarial.
- unknown: cualquier otra cosa.

RESPONDE SOLO CON UNA SOLA PALABRA. Sin explicaciones ni puntuación."""


def _keyword_classify(intent_lower: str) -> str:
    """Clasificación determinista por palabras clave — fallback rápido."""
    for domain, keywords in _KEYWORD_MAP.items():
        if any(kw in intent_lower for kw in keywords):
            return domain
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

    domain = "unknown"

    # ── Paso 1: Intentar clasificación semántica con LLM ─────────────────────
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from app.core.llm_factory import get_llm

        llm = get_llm(temperature=0)
        response = await llm.ainvoke([
            SystemMessage(content=_CLASSIFY_SYSTEM),
            HumanMessage(content=intent),
        ])
        raw = response.content.strip().lower().split()[0] if response.content else ""
        # Solo aceptar si el LLM devuelve un dominio válido
        if raw in VALID_DOMAINS:
            domain = raw
    except Exception as e:
        logger.debug("Fallo en clasificación LLM, usando fallback por palabras clave: %s", e)

    # ── Paso 2: Fallback por palabras clave si LLM no resolvió ───────────────
    if domain == "unknown":
        domain = _keyword_classify(intent_lower)

    return {
        **state,
        "classified_domain": domain,
        "status": TaskStatus.PLANNING,
        "iteration_count": state.get("iteration_count", 0) + 1,
    }


async def load_knowledge_node(state: OrchestratorState) -> dict:
    """Carga hechos y preferencias del TenantKnowledge para inyectar en el contexto."""
    from uuid import UUID
    from sqlalchemy import select
    from app.db.base import AsyncSessionLocal
    from app.db.models.models import TenantKnowledge

    tenant_id = state.get("tenant_id")
    if not tenant_id:
        return {"tenant_knowledge": []}

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(TenantKnowledge).where(TenantKnowledge.tenant_id == UUID(tenant_id))
            )
            facts = result.scalars().all()
            
            knowledge_list = [
                {"key": f.key, "value": f.value, "category": f.category}
                for f in facts
            ]
            return {"tenant_knowledge": knowledge_list}
    except Exception as e:
        print(f"Error cargando conocimiento: {e}")
        return {"tenant_knowledge": []}


async def plan_node(state: OrchestratorState) -> dict:
    """
    Descompone la tarea en subtareas.
    Si hay un workflow_id en los metadatos, carga el blueprint (nodos y aristas) de la base de datos.
    Sino, usa el LLM para dividir la tarea compleja si el dominio es 'coordinator'.
    """
    from uuid import UUID
    from sqlalchemy import select
    from app.db.base import AsyncSessionLocal
    from app.db.models.models import Workflow

    # ── Atajo 1: Seguir un Blueprint de Workflow si existe ───────────────────
    workflow_id = (state.get("additional_metadata") or {}).get("workflow_id")
    if workflow_id:
        try:
            async with AsyncSessionLocal() as db:
                wf_res = await db.execute(select(Workflow).where(Workflow.id == UUID(workflow_id)))
                wf = wf_res.scalar_one_or_none()

                if wf and wf.ui_nodes:
                    # ── Si tiene nodos avanzados, delegar al NodeEngine ──
                    from app.services.node_engine import has_advanced_nodes
                    if has_advanced_nodes(wf.ui_nodes):
                        print(f"[PLAN] Workflow '{wf.name}' tiene nodos avanzados → delegando a NodeEngine")
                        execution_id = (state.get("additional_metadata") or {}).get("execution_id")
                        if execution_id:
                            try:
                                from app.workers.celery_app import run_node_engine
                                run_node_engine.delay(execution_id)
                            except Exception as ce:
                                print(f"[PLAN] Error lanzando NodeEngine: {ce}")
                        return {
                            "plan": [{"id": "node_engine", "agent": "node_engine", "action": "delegated", "params": {}, "depends_on": [], "status": "done"}],
                            "status": TaskStatus.DONE,
                        }

                    print(f"[PLAN] Siguiendo blueprint del workflow '{wf.name}'")
                    plan: list[SubTask] = []

                    # Filtrar solo nodos de tipo action/skill
                    action_nodes = [n for n in wf.ui_nodes if n.get("type") in ("action", "skill")]
                    edges = wf.ui_edges or []

                    for node in action_nodes:
                        node_id = node["id"]
                        data = node.get("data", {})

                        # Determinar dependencias basándonos en las aristas
                        deps = [e["source"] for e in edges if e["target"] == node_id]

                        # Solo dependemos de nodos que también estén en el plan (purgar triggers)
                        final_deps = [d for d in deps if any(an["id"] == d for an in action_nodes)]

                        plan.append({
                            "id": node_id,
                            "agent": data.get("domain", "coordinator"),
                            "action": "execute_node",
                            "params": {"intent": data.get("instruction") or data.get("label", state["user_intent"]), "original_node_id": node_id},
                            "depends_on": final_deps,
                            "status": "pending",
                        })

                    if plan:
                        return {"plan": plan, "status": TaskStatus.EXECUTING}
        except Exception as e:
            print(f"[PLAN] Error cargando blueprint: {e}. Cayendo a planificación estándar.")

    domain = state["classified_domain"]
    
    if domain == "coordinator":
        try:
            from langchain_ollama import ChatOllama
            from pydantic import BaseModel, Field
            
            class PlanStep(BaseModel):
                agent: str = Field(description="Dominios válidos: hr, crm, excel, email, billing, documents, banking, rag")
                action: str = Field(description="Acción corta, ej: extract_data, create_report, send_email")
                instruction: str = Field(description="Instrucción muy detallada en español para el agente actual que ejecutará el paso.")

            class MultiAgentPlan(BaseModel):
                steps: list[PlanStep] = Field(description="Lista ordenada de pasos secuenciales para solventar el complejo problema")

            from app.core.config import settings
            from app.core.llm_factory import get_llm
            llm = get_llm(temperature=0)
            structured_llm = llm.with_structured_output(MultiAgentPlan, method="json_mode")
            
            prompt = (
                "Eres el Coordinador General. Descompón la siguiente petición en pasos ordenados y mínimos, usando SOLO los agentes necesarios.\n"
                "Esta es una ejecución única: produce un resultado final, NO crees reglas recurrentes.\n"
                f"Intención del usuario: {state['user_intent']}\n\n"
                "Agentes disponibles y cuándo usarlos:\n"
                "- email: revisar bandeja de entrada O enviar correos de confirmación.\n"
                "- crm: gestionar o buscar clientes/leads en CRM.\n"
                "- hr: consultar datos de empleados, nóminas o contratos laborales.\n"
                "- billing: crear o consultar facturas. Genera también el PDF automáticamente.\n"
                "- banking: consultar saldos o movimientos bancarios.\n"
                "- documents: archivar texto o informe como documento (NO para facturas, que las guarda billing directamente).\n\n"
                "REGLAS CRÍTICAS:\n"
                "1. NO incluyas 'excel' salvo que el usuario pida explícitamente cruzar ficheros Excel o CSV.\n"
                "2. NO incluyas 'documents' para guardar facturas (billing ya lo hace internamente).\n"
                "3. El número MÍNIMO de pasos posible. Evita pasos redundantes.\n"
                "4. El paso final debe ser 'email' si el usuario pide notificación.\n\n"
                "IMPORTANTE: Responde ÚNICAMENTE con JSON válido con EXACTAMENTE esta estructura:\n"
                '{"steps": [{"agent": "nombre_agente", "action": "accion_corta", "instruction": "instruccion detallada en español"}]}'
            )
            
            import asyncio as _asyncio
            plan_result = None
            last_exc = None
            for _attempt in range(3):
                try:
                    plan_result = structured_llm.invoke(prompt)
                    break
                except Exception as _e:
                    last_exc = _e
                    err_str = str(_e)
                    # Si es error de cuota de Gemini → fallback inmediato a Ollama
                    if "ResourceExhausted" in type(_e).__name__ or "429" in err_str or "quota" in err_str.lower():
                        print(f"[PLAN] Gemini cuota agotada, usando Ollama como fallback.")
                        from langchain_ollama import ChatOllama
                        from app.core.config import settings as _s
                        _fallback_llm = ChatOllama(model="llama3.2", base_url=_s.OLLAMA_BASE_URL, temperature=0)
                        structured_llm = _fallback_llm.with_structured_output(MultiAgentPlan, method="json_mode")
                        continue
                    # Si es error de red → esperar y reintentar
                    elif _attempt < 2:
                        import asyncio; await asyncio.sleep(5 * (_attempt + 1))
                    else:
                        raise

            if plan_result is None:
                raise last_exc or ValueError("No se pudo obtener respuesta del LLM")
             
            if not hasattr(plan_result, "steps") or plan_result.steps is None:
                raise ValueError("El LLM no devolvió los pasos en el formato esperado (faltan 'steps')")
            
            # Agentes válidos que no requieren archivos externos
            NON_FILE_AGENTS = {"email", "crm", "hr", "billing", "banking", "documents", "rag", "compliance"}
            
            plan: list[SubTask] = []
            for idx, step in enumerate(plan_result.steps):
                agent = step.agent if step.agent in VALID_DOMAINS else "unknown"
                plan.append({
                    "id": f"step_{idx+1}",
                    "agent": agent,
                    "action": step.action,
                    "params": {"intent": step.instruction},
                    "depends_on": [] if idx == 0 else [f"step_{idx}"],
                    "status": "pending",
                })
        except Exception as e:
            import traceback
            err_msg = traceback.format_exc()
            # Fallback seguro
            plan = [{
                "id": "step_1",
                "agent": "unknown",
                "action": "process",
                "params": {"intent": f"Plan fallido: {str(e)}\n\n{err_msg} -> {state['user_intent']}"},
                "depends_on": [],
                "status": "pending",
            }]
    else:
        plan: list[SubTask] = [
            {
                "id": "step_1",
                "agent": domain,
                "action": "process",
                "params": {"intent": state["user_intent"]},
                "depends_on": [],
                "status": "pending",
            }
        ]
        
    return {
        **state,
        "plan": plan,
        "status": TaskStatus.VALIDATING,
        "iteration_count": state["iteration_count"] + 1,
    }


async def validate_node(state: OrchestratorState) -> OrchestratorState:
    """
    Validación determinista pre-ejecución.
    Verifica que el plan es ejecutable antes de invocar ningún agente o LLM.
    """
    plan = state.get("plan", [])
    if not plan:
        return {
            **state,
            "status": TaskStatus.FAILED,
            "error_message": "El plan está vacío tras la fase de planificación",
        }

    # Aquí se añaden validaciones reales en Fase 1:
    # - NIF/CIF válido
    # - Importes dentro de rango
    # - Fechas coherentes
    # - Cliente existe en BD

    return {
        **state,
        "status": TaskStatus.EXECUTING,
        "iteration_count": state["iteration_count"] + 1,
    }


async def dispatch_node(state: OrchestratorState) -> OrchestratorState:
    """
    Invoca el agente especializado correspondiente al dominio de la subtarea.
    Usa ExecutionContext para enriquecer la intencion con los resultados previos,
    asegurando que cada agente sabe que hicieron los anteriores.
    """
    from app.services.execution_context import ExecutionContext

    plan = state["plan"]
    current_step = state["current_step"]

    if current_step >= len(plan):
        return {**state, "status": TaskStatus.DONE}

    subtask = plan[current_step]
    agent_name = subtask["agent"]

    # Construir contexto enriquecido con la instrucción específica del paso y outputs anteriores
    ctx = ExecutionContext.from_state(state)
    enriched_intent = ctx.build_enriched_intent(
        current_instruction=subtask.get("params", {}).get("intent")
    )
    enriched_state = {**state, "current_intent": enriched_intent}

    result: AgentResult

    if agent_name == "billing":
        result = await _dispatch_billing(enriched_state, subtask)
    elif agent_name == "documents":
        result = await _dispatch_documents(enriched_state, subtask)
    elif agent_name == "compliance":
        result = await _dispatch_compliance(enriched_state, subtask)
    elif agent_name == "banking":
        result = await _dispatch_banking(enriched_state, subtask)
    elif agent_name == "rag":
        result = await _dispatch_rag(enriched_state, subtask)
    elif agent_name == "crm":
        result = await _dispatch_crm(enriched_state, subtask)
    elif agent_name == "hr":
        result = await _dispatch_hr(enriched_state, subtask)
    elif agent_name == "excel":
        result = await _dispatch_excel(enriched_state, subtask)
    elif agent_name == "email":
        result = await _dispatch_email(enriched_state, subtask)
    elif agent_name == "workflow":
        result = await _dispatch_workflow(enriched_state, subtask)
    elif agent_name == "report":
        result = await _dispatch_report(enriched_state, subtask)
    elif agent_name == "skill" or agent_name.startswith("skill:"):
        result = await _dispatch_skill(enriched_state, subtask)
    else:
        if agent_name == "unknown":
            intent_param = subtask.get("params", {}).get("intent", "")
            if "Plan fallido:" in intent_param:
                message = f"Error interno al planificar la tarea compleja: {intent_param}"
                error_msg = intent_param
            else:
                message = "No he podido entender tu solicitud. Por favor, especifica si quieres crear una factura, revisar un documento, etc."
                error_msg = "Comando no reconocido."
        else:
            message = f"[PENDIENTE] Agente '{agent_name}' no implementado aún"
            error_msg = None

        result = {
            "subtask_id": subtask["id"],
            "agent": agent_name,
            "success": False if agent_name == "unknown" else True,
            "output": {"message": message},
            "error": error_msg,
        }

    # --- REGISTRO DE AUDITORÍA INMUTABLE ---
    import uuid

    from app.db.base import AsyncSessionLocal
    from app.services.audit import log_action
    
    action_str = result.get("output", {}).get("action", "unknown_action") if result.get("output") else "unknown_action"
    
    async def _safe_log():
        async with AsyncSessionLocal() as db:
            await log_action(
                db,
                tenant_id=uuid.UUID(state["tenant_id"]),
                task_id=uuid.UUID(state["task_id"]) if state.get("task_id") else None,
                agent_name=agent_name,
                action_type=action_str,
                status="success" if result["success"] else "failed",
                input_data={"subtask": subtask},
                output_data=result.get("output"),
                error_detail=result.get("error")
            )
            await db.commit()
    
    # Fire and forget el log
    import asyncio
    asyncio.create_task(_safe_log())
    # ----------------------------------------
    
    # Si el agente solicita aprobación humana, pausar el grafo
    if result.get("output", {}).get("action") == "approval_required":
        return {
            **state,
            "plan": plan,
            "agent_results": list(state["agent_results"]) + [result],
            "status": TaskStatus.AWAITING_APPROVAL,
            "requires_human_approval": True,
            "approval_id": result["output"].get("approval_id"),
            "iteration_count": state["iteration_count"] + 1,
        }

    new_results = list(state["agent_results"]) + [result]
    updated_plan = list(plan)
    updated_plan[current_step] = {**subtask, "status": "done" if result["success"] else "failed"}

    next_step = current_step + 1
    if not result["success"]:
        # Si el agente es "excel" o "documents" y falla, lo ignoramos y continuamos
        non_critical_agents = {"excel", "documents"}
        if agent_name in non_critical_agents:
            print(f"[ORCHESTRATOR] Agente no crítico '{agent_name}' falló, continuando con el siguiente paso.")
        else:
            return {
                **state,
                "plan": updated_plan,
                "agent_results": new_results,
                "status": TaskStatus.FAILED,
                "error_message": result.get("error"),
                "iteration_count": state["iteration_count"] + 1,
            }

    new_status = TaskStatus.DONE if next_step >= len(plan) else TaskStatus.EXECUTING
    return {
        **state,
        "plan": updated_plan,
        "agent_results": new_results,
        "current_step": next_step,
        "status": new_status,
        "iteration_count": state["iteration_count"] + 1,
    }


async def _dispatch_billing(state: OrchestratorState, subtask: dict) -> "AgentResult":
    """Invoca el billing agent y traduce su resultado al formato del orquestador."""
    import uuid

    from sqlalchemy import select

    from app.agents.billing_agent import run_billing_agent
    from app.db.base import AsyncSessionLocal
    from app.db.models.models import PendingApproval, TenantIntegration
    from app.services.encryption import decrypt_credentials

    tenant_id = state["tenant_id"]

    # Obtener API key de Holded si está configurada (opcional — modo local funciona sin Holded)
    holded_api_key: str | None = None
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TenantIntegration).where(
                TenantIntegration.tenant_id == uuid.UUID(tenant_id),
                TenantIntegration.integration_type == "holded",
                TenantIntegration.is_active.is_(True),
            )
        )
        integration = result.scalars().first()

    if integration:
        try:
            creds = decrypt_credentials(integration.encrypted_credentials)
            holded_api_key = creds.get("api_key")
        except Exception:
            holded_api_key = None  # Fallo al descifrar → modo local

    agent_result = await run_billing_agent(
        user_intent=state.get("current_intent", state["user_intent"]),
        tenant_id=tenant_id,
        holded_api_key=holded_api_key,
        task_id=state["task_id"],
    )

    if agent_result.action == "approval_required":
        # Guardar en BD para que el dashboard lo muestre
        async with AsyncSessionLocal() as db:
            approval = PendingApproval(
                task_id=uuid.UUID(state["task_id"]),
                tenant_id=uuid.UUID(tenant_id),
                action_description=(
                    f"Crear factura de {agent_result.extracted_data.get('amount_base', '?')}€ "
                    f"+ IVA {agent_result.extracted_data.get('vat_rate', '?')}% "
                    f"a {agent_result.extracted_data.get('client_name', '?')}"
                ),
                action_payload=agent_result.extracted_data or {},
                risk_level="high",
                expires_at=datetime.now(UTC) + timedelta(hours=2),
            )
            db.add(approval)
            await db.commit()
            await db.refresh(approval)
            approval_id = str(approval.id)

        return {
            "subtask_id": subtask["id"],
            "agent": "billing",
            "success": True,
            "output": {"action": "approval_required", "approval_id": approval_id},
            "error": None,
        }

    billing_result = {
        "subtask_id": subtask["id"],
        "agent": "billing",
        "success": agent_result.success,
        "output": {
            "action": agent_result.action,
            "holded_invoice_id": agent_result.holded_invoice_id,
            "extracted_data": agent_result.extracted_data,
            "warnings": agent_result.validation_warnings,
        },
        "error": agent_result.error or (
            "; ".join(agent_result.validation_errors) if agent_result.validation_errors else None
        ),
    }

    # Guardar resultado como documento PDF si fue exitoso (factura)
    if agent_result.success and agent_result.action == "draft_created":
        await _save_billing_result_as_pdf(
            state=state,
            agent_result=agent_result,
            tenant_id=state["tenant_id"],
            task_id=state["task_id"],
        )
    
    # Exportar a CSV si es un informe/consulta para que Excel pueda cruzarlo
    if agent_result.success and agent_result.action == "summary" and "invoices" in agent_result.extracted_data:
        # 1. Guardar CSV para procesamiento del agente de Excel
        await _save_ai_result_as_csv(
            tenant_id=state["tenant_id"],
            task_id=state["task_id"],
            category="facturas",
            filename=f"listado_facturas_{state['task_id'][:8]}.csv",
            data=agent_result.extracted_data["invoices"]
        )
        # 2. Guardar reporte legible en el Scanner (carpeta Facturas)
        invoices_text = "\n".join([
            f"- {i['numero']}: {i['cliente']} ({i['total']}€) - {i['estado']}" 
            for i in agent_result.extracted_data["invoices"]
        ])
        await _save_ai_result_as_document(
            tenant_id=tenant_id,
            task_id=state["task_id"],
            category="facturas",
            title=f"Listado de Facturas — {state['task_id'][:8]}",
            content=f"Reporte de facturación solicitado.\nTotal facturado: {agent_result.extracted_data.get('total', 0)}€\n\nDetalle:\n{invoices_text}"
        )

    return billing_result


async def _save_billing_result_as_pdf(
    state: OrchestratorState,
    agent_result,
    tenant_id: str,
    task_id: str,
) -> None:
    """
    Genera un PDF real de la factura creada por el billing agent IA
    y lo registra en TenantDocument (categoría 'facturas').
    Si ya existe un documento con el mismo task_id, lo sobreescribe.
    """
    import os
    import uuid

    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    from app.db.models.models import Tenant, TenantDocument
    from app.services.pdf_service import generate_invoice_pdf

    try:
        data = agent_result.extracted_data or {}
        _THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        upload_dir = os.path.normpath(os.path.join(_THIS_DIR, "..", "uploads"))
        os.makedirs(upload_dir, exist_ok=True)

        # Datos de la empresa emisora: priorizar los que vengan del prompt (issuer_*),
        # y si no existen, usar los del tenant como valor por defecto.
        async with AsyncSessionLocal() as db:
            tenant_obj = await db.get(Tenant, uuid.UUID(tenant_id))
        company_name = tenant_obj.name if tenant_obj else "Mi Empresa S.L."
        company_nif = data.get("issuer_nif") or (tenant_obj.nif if tenant_obj else "B00000000")
        company_address = data.get("issuer_address") or "Calle Principal, 1 · Madrid"
        company_email = data.get("issuer_email") or ""

        # Nombre de fichero determinista para poder sobreescribir en actualizaciones IA
        # Si los datos traen un número de factura real, lo usamos como clave de sobreescritura
        invoice_ref = data.get("invoice_number") or f"ia_{task_id[:8]}"
        filename = f"factura_{invoice_ref.replace('/', '_').lower()}.pdf"
        file_path = os.path.join(upload_dir, filename)

        # Construir datos para el PDF
        invoice_number = f"IA-{task_id[:8].upper()}"
        invoice_data = {
            "number": invoice_number,
            "date": data.get("invoice_date") or datetime.now().strftime("%Y-%m-%d"),
            "amount_base": float(data.get("amount_base") or 0),
            "tax_amount": round(
                float(data.get("amount_base") or 0) * float(data.get("vat_rate") or 21) / 100, 2
            ),
            "amount_total": round(
                float(data.get("amount_base") or 0) * (1 + float(data.get("vat_rate") or 21) / 100), 2
            ),
            "client": {
                "name": data.get("client_name") or "Cliente",
                "nif": data.get("client_nif") or "",
                "email": "",
                "address": "",
            },
            "company": {
                "name": company_name,
                "nif": company_nif,
                "address": company_address,
                "phone": "",
                "email": company_email,
            },
            "lines": [
                {
                    "description": data.get("concept") or "Servicio",
                    "quantity": 1.0,
                    "unit_price": float(data.get("amount_base") or 0),
                    "tax_percentage": float(data.get("vat_rate") or 21),
                    "total": round(
                        float(data.get("amount_base") or 0) * (1 + float(data.get("vat_rate") or 21) / 100), 2
                    ),
                }
            ],
        }
        if data.get("notes"):
            invoice_data["notes"] = data["notes"]
        if data.get("payment_terms") or data.get("payment_method"):
            invoice_data["payment_terms"] = data.get("payment_terms") or data.get("payment_method")

        pdf_bytes = generate_invoice_pdf(invoice_data)
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        async with AsyncSessionLocal() as db:
            existing_result = await db.execute(
                select(TenantDocument).where(
                    TenantDocument.tenant_id == uuid.UUID(tenant_id),
                    TenantDocument.category == "facturas",
                    or_(
                        TenantDocument.file_name == filename,
                        TenantDocument.task_id == uuid.UUID(task_id)
                    )
                )
            )
            existing_doc = existing_result.scalars().first()

            if existing_doc:
                # Bloqueo para concurrencia
                if not await _lock_document(db, existing_doc.id, uuid.UUID(task_id)):
                    print(f"[ORCHESTRATOR] Factura {filename} bloqueada. Reintentando...")

                # Sobreescribir el PDF existente
                existing_doc.file_path = file_path
                existing_doc.file_name = filename
                existing_doc.file_type = "application/pdf"
                existing_doc.file_size = len(pdf_bytes)
                existing_doc.processed_at = datetime.now(UTC)
                existing_doc.status = "completed"
                parsed = (
                    f"Factura IA: {invoice_number}\n"
                    f"Cliente: {data.get('client_name', 'N/A')}\n"
                    f"Concepto: {data.get('concept', 'N/A')}\n"
                    f"Base: {data.get('amount_base', 0)}€  IVA: {data.get('vat_rate', 21)}%\n"
                    f"Total: {invoice_data['amount_total']:.2f}€"
                )
                existing_doc.parsed_content = parsed
                # Desbloqueo
                await _unlock_document(db, existing_doc.id, uuid.UUID(task_id))
            else:
                parsed = (
                    f"Factura IA: {invoice_number}\n"
                    f"Cliente: {data.get('client_name', 'N/A')}\n"
                    f"Concepto: {data.get('concept', 'N/A')}\n"
                    f"Base: {data.get('amount_base', 0)}€  IVA: {data.get('vat_rate', 21)}%\n"
                    f"Total: {invoice_data['amount_total']:.2f}€"
                )
                doc = TenantDocument(
                    tenant_id=uuid.UUID(tenant_id),
                    task_id=uuid.UUID(task_id),
                    file_name=filename,
                    file_path=file_path,
                    file_type="application/pdf",
                    file_size=len(pdf_bytes),
                    category="facturas",
                    status="completed",
                    parsed_content=parsed,
                )
                db.add(doc)
            await db.commit()
    except Exception:
        import traceback
        traceback.print_exc()


# ── Mapeo tipo de documento → carpeta (category) ────────────────────────────
_DOC_TYPE_TO_CATEGORY = {
    "factura": "facturas",
    "factura_recibida": "facturas",
    "factura_emitida": "facturas",
    "presupuesto": "facturas",
    "nomina": "nominas",
    "recibo_salario": "nominas",
    "extracto_bancario": "bancos",
    "movimiento_bancario": "bancos",
    "contrato": "rrhh",
    "contrato_laboral": "rrhh",
    "certificado": "rrhh",
    "modelo_fiscal": "fiscal",
    "impuesto": "fiscal",
    "declaracion": "fiscal",
    "excel": "excels",
    "hoja_calculo": "excels",
    "informe": "informes",
    "correo": "correos",
    "email": "correos",
}


def _classify_document_category(document_type: str | None) -> str:
    """Mapea el tipo detectado por documents_agent a la carpeta correcta."""
    if not document_type:
        return "otros"
    doc_lower = document_type.lower().strip()
    # Coincidencia exacta
    if doc_lower in _DOC_TYPE_TO_CATEGORY:
        return _DOC_TYPE_TO_CATEGORY[doc_lower]
    # Coincidencia parcial
    for key, category in _DOC_TYPE_TO_CATEGORY.items():
        if key in doc_lower or doc_lower in key:
            return category
    return "otros"


async def _dispatch_documents(state: OrchestratorState, subtask: dict) -> "AgentResult":
    """Invoca el agente de documentos (OCR + clasificación + subida a Holded)."""
    import uuid

    from sqlalchemy import select

    from app.agents.documents_agent import run_documents_agent
    from app.db.base import AsyncSessionLocal
    from app.db.models.models import TenantDocument, TenantIntegration
    from app.services.encryption import decrypt_credentials

    tenant_id = state["tenant_id"]
    task_id   = state["task_id"]
    azure_endpoint = azure_key = holded_key = None
    file_bytes: bytes | None = None
    file_name: str | None = None
    file_content_type: str | None = None

    async with AsyncSessionLocal() as db:
        # ── Credenciales de Azure (OCR) ──────────────────────────────────
        az_result = await db.execute(
            select(TenantIntegration).where(
                TenantIntegration.tenant_id == uuid.UUID(tenant_id),
                TenantIntegration.integration_type == "azure_forms",
                TenantIntegration.is_active.is_(True),
            )
        )
        az_integration = az_result.scalars().first()
        if az_integration:
            try:
                creds = decrypt_credentials(az_integration.encrypted_credentials)
                azure_endpoint = creds.get("endpoint")
                azure_key      = creds.get("api_key")
            except Exception as e:
                logger.warning("Error al descifrar credenciales de Azure Forms para tenant %s: %s", tenant_id, e)

        # ── Credenciales de Holded (adjunto al contacto) ─────────────────
        hld_result = await db.execute(
            select(TenantIntegration).where(
                TenantIntegration.tenant_id == uuid.UUID(tenant_id),
                TenantIntegration.integration_type == "holded",
                TenantIntegration.is_active.is_(True),
            )
        )
        hld_integration = hld_result.scalars().first()
        if hld_integration:
            try:
                creds = decrypt_credentials(hld_integration.encrypted_credentials)
                holded_key = creds.get("api_key")
            except Exception as e:
                logger.warning("Error al descifrar credenciales de Holded para tenant %s: %s", tenant_id, e)

        # ── Leer el archivo desde disco (buscar por task_id) ─────────────
        doc_result = await db.execute(
            select(TenantDocument).where(TenantDocument.task_id == uuid.UUID(task_id))
        )
        linked_doc = doc_result.scalars().first()
        if linked_doc and linked_doc.file_path:
            try:
                with open(linked_doc.file_path, "rb") as f:
                    file_bytes = f.read()
                file_name = linked_doc.file_name
                file_content_type = linked_doc.file_type or "application/pdf"
            except Exception as e:
                logger.warning("Error al leer archivo del documento vinculado %s desde disco: %s", linked_doc.file_path, e)

    agent_result = await run_documents_agent(
        user_intent=state.get("current_intent", state["user_intent"]),
        file_bytes=file_bytes,
        file_content_type=file_content_type or "application/pdf",
        azure_endpoint=azure_endpoint,
        azure_api_key=azure_key,
        holded_api_key=holded_key,
        holded_file_name=file_name,
        holded_file_content_type=file_content_type,
        tenant_id=tenant_id,
        document_id=task_id,
    )

    holded_info = agent_result.holded_upload or {}
    
    # Archivar siempre el resultado del análisis de documentos
    await _save_ai_result_as_document(
        tenant_id=tenant_id,
        task_id=state["task_id"],
        category=_classify_document_category(agent_result.document_type),
        title=f"Análisis Documento — {file_name or 'Sin Nombre'}",
        content=(
            f"Tipo detectado: {agent_result.document_type}\n"
            f"Entidades: {agent_result.classified.key_entities if agent_result.classified else 'N/A'}\n"
            f"Acción Holded: {holded_info.get('reason', 'N/A')}"
        )
    )

    return {
        "subtask_id": subtask["id"],
        "agent": "documents",
        "success": agent_result.success,
        "output": {
            "document_type":   agent_result.document_type,
            "classified":      agent_result.classified.model_dump() if agent_result.classified else None,
            "requires_review": agent_result.requires_review,
            "holded_adjunto":  holded_info.get("uploaded", False),
            "holded_contacto": holded_info.get("contact_name", ""),
            "holded_reason":   holded_info.get("reason", ""),
        },
        "error": agent_result.error,
    }


async def _dispatch_compliance(state: OrchestratorState, subtask: dict) -> "AgentResult":
    """Invoca el agente de compliance fiscal."""
    from app.agents.compliance_agent import run_compliance_agent

    agent_result = await run_compliance_agent(
        user_intent=state.get("current_intent", state["user_intent"]),
        tenant_id=state["tenant_id"],
    )

    # Guardar resultado como documento si fue exitoso
    if agent_result.success:
        content_parts = []
        if agent_result.respuesta_consulta:
            content_parts.append(f"Respuesta: {agent_result.respuesta_consulta}")
        if agent_result.alertas_redactadas:
            content_parts.append("Alertas:\n" + "\n".join(f"- {a}" for a in agent_result.alertas_redactadas))
        if agent_result.vencimientos_proximos:
            content_parts.append("Vencimientos:\n" + "\n".join(f"- {v}" for v in agent_result.vencimientos_proximos))
        if agent_result.resumen_boe:
            content_parts.append(f"Novedades BOE: {agent_result.resumen_boe}")
        await _save_ai_result_as_document(
            tenant_id=state["tenant_id"],
            task_id=state["task_id"],
            category="fiscal",
            title=f"Informe Fiscal IA — {state['user_intent'][:60]}",
            content="\n\n".join(content_parts) if content_parts else "Análisis completado sin contenido exportable.",
        )

    return {
        "subtask_id": subtask["id"],
        "agent": "compliance",
        "success": agent_result.success,
        "output": {
            "action":               agent_result.action,
            "vencimientos":         agent_result.vencimientos_proximos,
            "alertas":              agent_result.alertas_redactadas,
            "boe_novedades":        agent_result.boe_novedades,
            "resumen_boe":          agent_result.resumen_boe,
            "respuesta_consulta":   agent_result.respuesta_consulta,
        },
        "error": agent_result.error,
    }


async def _dispatch_banking(state: OrchestratorState, subtask: dict) -> "AgentResult":
    """Invoca el agente bancario."""
    import uuid

    from sqlalchemy import select

    from app.agents.banking_agent import run_banking_agent
    from app.db.base import AsyncSessionLocal
    from app.db.models.models import TenantIntegration
    from app.services.encryption import decrypt_credentials

    tenant_id = state["tenant_id"]
    nordigen_id = nordigen_key = None

    # Obtener credenciales de PSD2 si están configuradas
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TenantIntegration).where(
                TenantIntegration.tenant_id == uuid.UUID(tenant_id),
                TenantIntegration.integration_type == "psd2",
                TenantIntegration.is_active.is_(True),
            )
        )
        integration = result.scalars().first()

    if integration:
        try:
            creds = decrypt_credentials(integration.encrypted_credentials)
            nordigen_id = creds.get("secret_id")
            nordigen_key = creds.get("secret_key")
        except Exception as e:
            logger.warning("Error al descifrar credenciales PSD2 para tenant %s: %s", tenant_id, e)

    agent_result = await run_banking_agent(
        user_intent=subtask.get("params", {}).get("intent", state.get("current_intent", state["user_intent"])),
        tenant_id=tenant_id,
        nordigen_secret_id=nordigen_id,
        nordigen_secret_key=nordigen_key,
        account_ids=["acc_demo_123"],  # Mocked account
    )

    # Guardar resultado como documento si fue exitoso
    if agent_result.success:
        content_parts = []
        if agent_result.resumen_financiero:
            content_parts.append(f"Resumen financiero:\n{agent_result.resumen_financiero}")
        if agent_result.saldos:
            saldos_txt = "\n".join(f"  • {s.get('nombre', 'Cuenta')} ({s.get('iban')}): {s.get('saldo')} {s.get('moneda', 'EUR')}" for s in agent_result.saldos)
            content_parts.append(f"Saldos:\n{saldos_txt}")
        if agent_result.alertas:
            content_parts.append("Alertas:\n" + "\n".join(f"- {a}" for a in agent_result.alertas))
        await _save_ai_result_as_document(
            tenant_id=tenant_id,
            task_id=state["task_id"],
            category="bancos",
            title=f"Informe Bancario IA — {state['user_intent'][:60]}",
            content="\n\n".join(content_parts) if content_parts else "Análisis bancario completado.",
        )
        # Exportar transacciones a CSV para que el agente de Excel pueda procesarlas
        if agent_result.transacciones:
            await _save_ai_result_as_csv(
                tenant_id=tenant_id,
                task_id=state["task_id"],
                category="bancos",
                filename=f"movimientos_bancos_{state['task_id'][:8]}.csv",
                data=agent_result.transacciones
            )

    return {
        "subtask_id": subtask["id"],
        "agent": "banking",
        "success": agent_result.success,
        "output": {
            "action":             agent_result.action,
            "resumen_financiero": agent_result.resumen_financiero,
            "saldos":             agent_result.saldos,
            "transacciones":      agent_result.transacciones,
            "alertas":            agent_result.alertas,
        },
        "error": agent_result.error,
    }


async def _dispatch_rag(state: OrchestratorState, subtask: dict) -> "AgentResult":
    """Invoca el agente de RAG para consulta de documentos."""
    from app.agents.rag_agent import run_rag_agent

    tenant_id = state["tenant_id"]

    agent_result = await run_rag_agent(
        user_intent=subtask.get("params", {}).get("intent", state.get("current_intent", state["user_intent"])),
        tenant_id=tenant_id,
        top_k=5
    )

    # Guardar respuesta RAG como documento en el Escáner
    if agent_result.success:
        sources = agent_result.sources_used
        if isinstance(sources, (list, tuple, set)):
            sources_str = ', '.join(str(s) for s in sources)
        else:
            sources_str = str(sources) if sources else 'N/A'
            
        await _save_ai_result_as_document(
            tenant_id=tenant_id,
            task_id=state["task_id"],
            category="informes",
            title=f"Consulta Documental — {state['user_intent'][:60]}",
            content=f"Pregunta: {subtask.get('params', {}).get('intent')}\n\nRespuesta:\n{agent_result.answer}\n\nFuentes: {sources_str}"
        )

    return {
        "subtask_id": subtask["id"],
        "agent": "rag",
        "success": agent_result.success,
        "output": {
            "answer": agent_result.answer,
            "sources_used": agent_result.sources_used,
        },
        "error": agent_result.error,
    }


async def _dispatch_crm(state: OrchestratorState, subtask: dict) -> "AgentResult":
    """Invoca el agente de ventas/CRM — modo determinista:
    1. Crea una oportunidad de venta directamente en la BD.
    2. Guarda el resultado como documento en el Escáner.
    """
    import asyncio
    import uuid

    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    from app.db.models.models import Client, Opportunity

    tenant_id = state["tenant_id"]
    intent = subtask.get("params", {}).get("intent", state.get("current_intent", state["user_intent"]))

    action_taken = "Asistencia CRM completada."
    success = True

    try:
        async with AsyncSessionLocal() as db:
            # Buscar cualquier cliente del tenant
            client_result = await db.execute(
                select(Client)
                .where(Client.tenant_id == uuid.UUID(tenant_id))
                .order_by(Client.created_at.desc())
                .limit(1)
            )
            client = client_result.scalars().first()

            if client:
                # Verificar si ya tiene una oportunidad activa
                opp_result = await db.execute(
                    select(Opportunity).where(
                        Opportunity.tenant_id == uuid.UUID(tenant_id),
                        Opportunity.client_id == client.id,
                        Opportunity.stage.not_in(["won", "lost"])
                    ).limit(1)
                )
                existing_opp = opp_result.scalars().first()

                if existing_opp:
                    # Avanzar el estado del lead existente
                    old_stage = existing_opp.stage
                    stage_map = {"new": "qualified", "qualified": "proposal", "proposal": "won"}
                    new_stage = stage_map.get(old_stage, "qualified")
                    existing_opp.stage = new_stage
                    await db.commit()
                    action_taken = (
                        f"Lead del cliente {client.name} avanzado de '{old_stage}' a '{new_stage}' "
                        f"en el embudo de ventas. ID: {existing_opp.id}"
                    )
                else:
                    # Crear nueva oportunidad
                    new_opp = Opportunity(
                        tenant_id=uuid.UUID(tenant_id),
                        client_id=client.id,
                        title=f"Oportunidad IA — {client.name}",
                        expected_value=5000.0,
                        stage="new"
                    )
                    db.add(new_opp)
                    await db.commit()
                    await db.refresh(new_opp)
                    action_taken = (
                        f"Nueva oportunidad de venta creada para {client.name} "
                        f"en fase 'new' por 5.000€. ID: {new_opp.id}"
                    )
            else:
                action_taken = "No hay clientes registrados en el CRM aún."
    except Exception as e:
        success = False
        action_taken = f"Error en CRM: {str(e)}"

    # Guardar resultado como documento visible en el Escáner
    await _save_ai_result_as_document(
            tenant_id=tenant_id,
            task_id=state["task_id"],
            category="crm",
            title=f"Informe CRM — {state['user_intent'][:60]}",
            content=action_taken
        )

    return {
        "subtask_id": subtask["id"],
        "agent": "crm",
        "success": success,
        "output": {"action": action_taken},
        "error": None if success else action_taken,
    }




# --- SISTEMA DE BLOQUEO Y CONCURRENCIA ---
import uuid

async def _lock_document(db, doc_id: uuid.UUID, task_id: uuid.UUID) -> bool:
    """Intenta bloquear un documento para una tarea específica."""
    from app.db.models.models import TenantDocument
    from datetime import datetime, UTC
    
    doc = await db.get(TenantDocument, doc_id)
    if not doc:
        return False
    
    # Si ya está bloqueado por otra tarea activa (hace menos de 5 min)
    if doc.locked_by and doc.locked_by != task_id:
        if doc.locked_at and (datetime.now(UTC) - doc.locked_at).total_seconds() < 300:
            return False
            
    doc.locked_by = task_id
    doc.locked_at = datetime.now(UTC)
    return True

async def _unlock_document(db, doc_id: uuid.UUID, task_id: uuid.UUID):
    """Libera el bloqueo de un documento."""
    from app.db.models.models import TenantDocument
    doc = await db.get(TenantDocument, doc_id)
    if doc and doc.locked_by == task_id:
        doc.locked_by = None
        doc.locked_at = None

async def _save_ai_result_as_document(
    tenant_id: str,
    task_id: str,
    category: str,
    title: str,
    content: str,
    reference_name: str | None = None  # Si se especifica, se busca para sobreescribir
) -> None:
    """
    Guarda el resultado textual de un Agente IA como un documento PDF.
    Implementa lógica de SOBREESCRITURA si existe un documento similar en la carpeta.
    """
    import os
    import uuid
    from datetime import datetime, UTC

    from sqlalchemy import select, and_, or_

    from app.db.base import AsyncSessionLocal
    from app.db.models.models import TenantDocument
    from app.services.pdf_service import generate_text_report_pdf

    try:
        # Ruta de uploads
        _THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        upload_dir = os.path.normpath(os.path.join(_THIS_DIR, "..", "uploads"))
        os.makedirs(upload_dir, exist_ok=True)

        # Nombre de fichero determinista (ahora .pdf)
        # Si hay un reference_name (ej: "factura_123"), lo usamos para ser constantes
        clean_ref = "".join(c for c in (reference_name or title) if c.isalnum() or c in (' ', '_', '-')).replace(' ', '_').lower()
        filename = f"{category.lower()}_{clean_ref[:30]}.pdf"
        file_path = os.path.join(upload_dir, filename)
        
        # Generar PDF desde el contenido
        pdf_bytes = generate_text_report_pdf(title, content, category)

        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        async with AsyncSessionLocal() as db:
            # Buscar si ya existe un doc similar para SOBREESCRIBIR
            # Priorizamos buscar por nombre de archivo o título en la misma categoría
            existing_result = await db.execute(
                select(TenantDocument).where(
                    TenantDocument.tenant_id == uuid.UUID(tenant_id),
                    TenantDocument.category == category,
                    or_(
                        TenantDocument.file_name == filename,
                        TenantDocument.task_id == uuid.UUID(task_id)
                    )
                )
            )
            existing_doc = existing_result.scalars().first()

            if existing_doc:
                # INTENTAR BLOQUEO PARA CONCURRENCIA
                if not await _lock_document(db, existing_doc.id, uuid.UUID(task_id)):
                    print(f"[ORCHESTRATOR] Archivo {filename} bloqueado por otro agente. Esperando...")
                    # En una implementación real, reintentaríamos. Aquí lo forzamos tras aviso si es el mismo task
                
                # Sobreescribir: actualizar campos
                existing_doc.file_path = file_path
                existing_doc.file_name = filename
                existing_doc.file_type = "application/pdf"
                existing_doc.file_size = len(pdf_bytes)
                existing_doc.processed_at = datetime.now(UTC)
                existing_doc.status = "completed"
                existing_doc.parsed_content = content
                
                # Liberar bloqueo
                await _unlock_document(db, existing_doc.id, uuid.UUID(task_id))
            else:
                doc = TenantDocument(
                    tenant_id=uuid.UUID(tenant_id),
                    task_id=uuid.UUID(task_id),
                    file_name=filename,
                    file_path=file_path,
                    file_type="application/pdf",
                    file_size=len(pdf_bytes),
                    category=category,
                    status="completed",
                    parsed_content=content,
                )
                db.add(doc)
            await db.commit()
    except Exception:
        import traceback
        traceback.print_exc()  # Log completo para debugging sin silenciar


async def _dispatch_hr(state: OrchestratorState, subtask: dict) -> "AgentResult":
    """Invoca el agente de Recursos Humanos — modo determinista:
    1. Extrae NIF del prompt usando el LLM.
    2. Llama directamente a _create_payroll_async para crear la nómina y PDF.
    3. Guarda el resultado como documento visible.
    """
    import re
    import uuid

    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    from app.db.models.models import Employee
    from app.agents.hr_agent import _create_payroll_async

    tenant_id = state["tenant_id"]
    intent = subtask.get("params", {}).get("intent", state.get("current_intent", state["user_intent"]))

    # Extraer NIF del intent con regex (patrón español: 8 dígitos + letra)
    nif_match = re.search(r'\b(\d{8}[A-Z])\b', intent.upper())
    nif = nif_match.group(1) if nif_match else None

    # Extraer mes/año del intent con lógica robusta de lenguaje natural
    month, year = _extract_month_year(intent)

    action_taken = ""
    success = True

    try:
        if not nif:
            # Si no hay NIF en el prompt, tomar el primer empleado activo
            async with AsyncSessionLocal() as db:
                emp_result = await db.execute(
                    select(Employee).where(
                        Employee.tenant_id == uuid.UUID(tenant_id),
                        Employee.status == "active"
                    ).limit(1)
                )
                emp = emp_result.scalars().first()
                nif = emp.nif if emp else None

        if not nif:
            action_taken = "No se encontró ningún empleado activo en RRHH."
            success = False
        else:
            action_taken = await _create_payroll_async(tenant_id, nif, month, year, 0.0)
    except Exception as e:
        success = False
        action_taken = f"Error generando nómina: {str(e)}"

    # Guardar resumen como documento txt adicional en el Escáner
    await _save_ai_result_as_document(
        tenant_id=tenant_id,
        task_id=state["task_id"],
        category="nominas",
        title=f"Resultado Nómina IA — {state['user_intent'][:60]}",
        content=action_taken
    )

    return {
        "subtask_id": subtask["id"],
        "agent": "hr",
        "success": success,
        "output": {"action": action_taken},
        "error": None if success else action_taken,
    }

# ─── Condiciones de enrutamiento ─────────────────────────────────────────────

def route_after_validate(state: OrchestratorState) -> str:
    if state["status"] == TaskStatus.FAILED:
        return "end"
    if state.get("requires_human_approval"):
        return "await_approval"
    return "dispatch"


def route_after_dispatch(state: OrchestratorState) -> str:
    if state["status"] == TaskStatus.FAILED:
        return "end"
    if state["status"] == TaskStatus.DONE:
        return "end"
    if state["status"] == TaskStatus.AWAITING_APPROVAL:
        return "end"  # Pausa: esperar aprobación humana antes de continuar
    if state["iteration_count"] >= MAX_ITERATIONS:
        return "end"
    return "dispatch"  # Continúa con siguiente subtarea


async def _dispatch_excel(state: OrchestratorState, subtask: dict) -> "AgentResult":
    from app.agents.excel_agent import run_excel_agent
    
    agent_result = await run_excel_agent(
        user_intent=subtask.get("params", {}).get("intent", state.get("current_intent", state["user_intent"])),
        tenant_id=state["tenant_id"],
        task_id=state["task_id"]
    )
    
    if agent_result.success:
        await _save_ai_result_as_document(
            tenant_id=state["tenant_id"],
            task_id=state["task_id"],
            category="informes",
            title=f"Análisis con Excel/Pandas — {state['task_id'][:8]}",
            content=f"Resultado de la operación de datos:\n{agent_result.output_message}"
        )

    return {
        "subtask_id": subtask["id"],
        "agent": "excel",
        "success": agent_result.success,
        "output": {"message": agent_result.output_message},
        "error": agent_result.error,
    }


async def _dispatch_email(state: OrchestratorState, subtask: dict) -> "AgentResult":
    """Invoca el agente de email y guarda su resultado como documento."""
    from app.agents.email_agent import run_email_agent

    agent_result = await run_email_agent(
        user_intent=subtask.get("params", {}).get("intent", state.get("current_intent", state["user_intent"])),
        tenant_id=state["tenant_id"],
        task_id=state["task_id"]
    )

    action = agent_result.action or "Operación de email completada."

    # Guardar siempre el resultado en el Scanner bajo la categoría correos
    try:
        await _save_ai_result_as_document(
            tenant_id=state["tenant_id"],
            task_id=state["task_id"],
            category="correos",
            title=f"Email: {state['user_intent'][:50]}...",
            content=action
        )
    except Exception as e:
        print(f"Error al archivar log de email: {e}")

    return {
        "subtask_id": subtask["id"],
        "agent": "email",
        "success": agent_result.success,
        "output": {"action": action},
        "error": agent_result.error,
    }


async def _dispatch_workflow(state: OrchestratorState, subtask: dict) -> "AgentResult":
    """Invoca el agente de gestión de Workflows / Automatizaciones."""
    from app.agents.workflow_agent import run_workflow_agent

    agent_result = await run_workflow_agent(
        user_intent=state.get("current_intent", state["user_intent"]),
        tenant_id=state["tenant_id"],
        user_id=state.get("user_id"),
        task_id=state.get("task_id"),
    )

    # Guardar configuración de automatización como documento
    if agent_result.success:
        await _save_ai_result_as_document(
            tenant_id=state["tenant_id"],
            task_id=state["task_id"],
            category="automatizaciones",
            title=f"Nueva Regla: {agent_result.workflow_name}",
            content=f"Acción: {agent_result.action}\nID: {agent_result.workflow_id}\n\nDetalle del plan:\n{agent_result.data}"
        )

    return {
        "subtask_id": subtask["id"],
        "agent": "workflow",
        "success": agent_result.success,
        "output": {
            "action": agent_result.action,
            "workflow_id": agent_result.workflow_id,
            "workflow_name": agent_result.workflow_name,
            "plan": agent_result.data,
        },
        "error": agent_result.error,
    }


async def _dispatch_report(state: OrchestratorState, subtask: dict) -> "AgentResult":
    """Genera el informe mensual de empresa y lo guarda como documento PDF."""
    intent = subtask.get("params", {}).get("intent", state.get("user_intent", ""))

    # Extraer mes del intent con lógica robusta de lenguaje natural
    _month, _year = _extract_month_year(intent)
    month_str = f"{_year}-{_month:02d}"

    try:
        import httpx as _httpx

        # Llamada interna al endpoint de generación de informes
        from app.core.config import settings as _s
        base_url = f"http://localhost:{getattr(_s, 'PORT', 8080)}"

        # Obtener token del estado para autenticar la petición interna
        # Si no hay token en estado, usamos la BD directamente
        from calendar import monthrange as _mr
        from datetime import UTC as _UTC, datetime as _dt

        from sqlalchemy.ext.asyncio import AsyncSession
        from app.db.base import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            from sqlalchemy import and_, func, select as _select
            from app.db.models.models import (
                BankTransaction, Client, Employee, Invoice, Payroll, Tenant, TenantDocument, User
            )
            from app.services.pdf_service import generate_snapshot_pdf

            tenant_id = state["tenant_id"]
            user_id = state["user_id"]

            year, mon = map(int, month_str.split("-"))
            start = _date(year, mon, 1)
            last_day = _mr(year, mon)[1]
            end = _date(year, mon, last_day)

            # Obtener nombre de empresa
            t_q = await db.execute(_select(Tenant).where(Tenant.id == tenant_id))
            tenant = t_q.scalar_one_or_none()
            company_name = tenant.name if tenant and tenant.name else "Tu empresa"

            # Facturas
            inv_q = await db.execute(
                _select(Invoice).where(
                    and_(
                        Invoice.tenant_id == tenant_id,
                        func.date(Invoice.date) >= start,
                        func.date(Invoice.date) <= end,
                    )
                )
            )
            invoices = inv_q.scalars().all()
            issued = [i for i in invoices if i.invoice_type == "issued"]
            received = [i for i in invoices if i.invoice_type == "received"]
            pending_issued = [i for i in issued if i.status in ("draft", "pending")]
            ingresos = sum(float(i.amount_total or 0) for i in issued)
            gastos = sum(float(i.amount_total or 0) for i in received)
            margen = ingresos - gastos
            margen_pct = round((margen / ingresos) * 100, 1) if ingresos > 0 else 0.0
            imp_pendiente = sum(float(i.amount_total or 0) for i in pending_issued)

            # Banca
            tx_q = await db.execute(
                _select(BankTransaction).where(
                    and_(
                        BankTransaction.tenant_id == tenant_id,
                        BankTransaction.date >= start,
                        BankTransaction.date <= end,
                    )
                )
            )
            txs = tx_q.scalars().all()
            bank_in = sum(float(t.amount) for t in txs if float(t.amount) > 0)
            bank_out = abs(sum(float(t.amount) for t in txs if float(t.amount) < 0))
            reconciled = sum(1 for t in txs if t.status == "reconciled")

            # RRHH
            emp_q = await db.execute(
                _select(Employee).where(and_(Employee.tenant_id == tenant_id, Employee.status == "active"))
            )
            employees = emp_q.scalars().all()
            payroll_q = await db.execute(
                _select(Payroll).where(
                    and_(
                        Payroll.tenant_id == tenant_id,
                        func.date(Payroll.period_start) >= start,
                        func.date(Payroll.period_end) <= end,
                    )
                )
            )
            payrolls = payroll_q.scalars().all()
            coste_nominas = sum(float(p.net_salary or 0) for p in payrolls)
            paid_payrolls = [p for p in payrolls if p.status == "paid"]

            # Clientes
            total_clients_q = await db.execute(
                _select(func.count()).select_from(Client).where(Client.tenant_id == tenant_id)
            )
            total_clients = total_clients_q.scalar() or 0
            new_clients_q = await db.execute(
                _select(func.count()).select_from(Client).where(
                    and_(
                        Client.tenant_id == tenant_id,
                        func.date(Client.created_at) >= start,
                        func.date(Client.created_at) <= end,
                    )
                )
            )
            new_clients = new_clients_q.scalar() or 0

            # Top client
            client_totals: dict = {}
            for inv in issued:
                cid = str(inv.client_id) if inv.client_id else None
                if cid:
                    client_totals[cid] = client_totals.get(cid, 0) + float(inv.amount_total or 0)
            top_client_name = None
            top_amount = 0.0
            if client_totals:
                top_cid = max(client_totals, key=client_totals.get)
                top_amount = client_totals[top_cid]
                cl_q = await db.execute(_select(Client).where(Client.id == top_cid))
                cl = cl_q.scalar_one_or_none()
                if cl:
                    top_client_name = cl.name

            # Resumen ejecutivo
            tendencia = "positiva" if margen > 0 else "negativa"
            resumen = (
                f"El mes {month_str} presenta una tendencia {tendencia}. "
                f"La empresa facturó {ingresos:,.2f} € con un margen bruto del {margen_pct:.1f}%. "
            )
            if pending_issued:
                resumen += f"Quedan {len(pending_issued)} facturas pendientes de cobro ({imp_pendiente:,.2f} €). "
            if employees:
                resumen += f"Plantilla activa: {len(employees)} empleados, coste nóminas {coste_nominas:,.2f} €. "
            if txs:
                resumen += f"Se registraron {len(txs)} movimientos bancarios."

            # Construir dict estructurado para PDF con gráficas
            snap_dict = {
                "facturas": {
                    "ingresos_total": ingresos,
                    "gastos_total": gastos,
                    "margen_bruto": margen,
                    "margen_pct": margen_pct,
                    "facturas_emitidas": len(issued),
                    "facturas_recibidas": len(received),
                    "facturas_pendientes_cobro": len(pending_issued),
                    "importe_pendiente_cobro": imp_pendiente,
                },
                "banca": {
                    "total_ingresos": bank_in,
                    "total_gastos": bank_out,
                    "saldo_neto": bank_in - bank_out,
                    "transacciones": len(txs),
                    "reconciliadas": reconciled,
                },
                "rrhh": {
                    "empleados_activos": len(employees),
                    "coste_nominas": coste_nominas,
                    "nominas_pagadas": len(paid_payrolls),
                    "nominas_pendientes": len(payrolls) - len(paid_payrolls),
                },
                "clientes": {
                    "total_clientes": total_clients,
                    "nuevos_periodo": new_clients,
                    "top_client_name": top_client_name,
                    "top_client_amount": top_amount,
                },
                "resumen_ejecutivo": resumen,
            }

            # Generar PDF con gráficas
            import os as _os, uuid as _uuid
            pdf_bytes = generate_snapshot_pdf(
                snap=snap_dict,
                company_name=company_name,
                month=month_str,
            )
            upload_dir = _os.path.join(_os.path.dirname(__file__), "..", "uploads")
            _os.makedirs(upload_dir, exist_ok=True)
            file_name = f"informe_{month_str}_{_uuid.uuid4().hex[:8]}.pdf"
            file_path = _os.path.join(upload_dir, file_name)
            with open(file_path, "wb") as fh:
                fh.write(pdf_bytes)

            # Guardar en tenant_documents
            doc = TenantDocument(
                id=_uuid.uuid4(),
                tenant_id=tenant_id,
                uploaded_by=user_id,
                file_name=file_name,
                file_type="application/pdf",
                file_path=file_path,
                file_size=len(pdf_bytes),
                status="processed",
                parsed_content=resumen,
                category="informes",
                created_at=_dt.now(_UTC),
                processed_at=_dt.now(_UTC),
            )
            db.add(doc)
            await db.commit()

        return {
            "subtask_id": subtask.get("id", "report_1"),
            "agent": "report",
            "success": True,
            "output": {
                "message": f"Informe mensual de {month_str} generado correctamente para {company_name}.",
                "file_name": file_name,
                "period": month_str,
                "resumen": resumen,
                "kpis": {
                    "ingresos": ingresos,
                    "gastos": gastos,
                    "margen_pct": margen_pct,
                    "empleados_activos": len(employees),
                    "pendiente_cobro": imp_pendiente,
                },
            },
            "error": None,
        }
    except Exception as exc:
        return {
            "subtask_id": subtask.get("id", "report_1"),
            "agent": "report",
            "success": False,
            "output": {},
            "error": f"Error generando informe mensual: {exc}",
        }


async def _dispatch_skill(state: OrchestratorState, subtask: dict) -> "AgentResult":
    """Invoca una Habilidad Modular (Skill) del registro dinámico."""
    from app.skills.registry import SkillRegistry
    
    agent_name = subtask["agent"]
    skill_name = agent_name
    if skill_name.startswith("skill:"):
        skill_name = skill_name[6:]
    
    # Intentar obtener de params si el agente es genérico 'skill'
    if skill_name == "skill":
        skill_name = subtask.get("params", {}).get("skill_name")
        
    if not skill_name:
        return {
            "subtask_id": subtask["id"],
            "agent": "skill",
            "success": False,
            "output": {},
            "error": "No se especificó el nombre de la Skill a ejecutar.",
        }

    skill = SkillRegistry.get_skill(skill_name)
    if not skill:
        # Fallback: intentar cargar builtins si por algún motivo no están
        SkillRegistry.load_builtins()
        skill = SkillRegistry.get_skill(skill_name)

    if not skill:
        return {
            "subtask_id": subtask["id"],
            "agent": "skill",
            "success": False,
            "output": {},
            "error": f"La Skill '{skill_name}' no está registrada en el sistema.",
        }

    try:
        # Ejecutar la skill
        payload = subtask.get("params", {})
        tenant_id = state.get("tenant_id")
        
        # Si la skill es asíncrona
        import inspect
        if inspect.iscoroutinefunction(skill.run):
            result_data = await skill.run(payload, tenant_id=tenant_id)
        else:
            result_data = skill.run(payload, tenant_id=tenant_id)

        return {
            "subtask_id": subtask["id"],
            "agent": f"skill:{skill_name}",
            "success": True,
            "output": result_data,
            "error": None,
        }
    except Exception as e:
        return {
            "subtask_id": subtask["id"],
            "agent": f"skill:{skill_name}",
            "success": False,
            "output": {},
            "error": f"Error ejecutando Skill '{skill_name}': {str(e)}",
        }


# ─── Construcción del grafo ───────────────────────────────────────────────────

def build_orchestrator() -> CompiledStateGraph:
    graph = StateGraph(OrchestratorState)

    graph.add_node("classify", classify_node)
    graph.add_node("load_knowledge", load_knowledge_node)
    graph.add_node("planner", plan_node)
    graph.add_node("validate", validate_node)
    graph.add_node("dispatch", dispatch_node)

    graph.set_entry_point("classify")
    graph.add_edge("classify", "load_knowledge")
    graph.add_edge("load_knowledge", "planner")
    graph.add_edge("planner", "validate")
    graph.add_conditional_edges(
        "validate",
        route_after_validate,
        {
            "dispatch": "dispatch",
            "await_approval": END,  # Pausa; se reanuda tras aprobación
            "end": END,
        },
    )
    graph.add_conditional_edges(
        "dispatch",
        route_after_dispatch,
        {
            "dispatch": "dispatch",
            "end": END,
        },
    )

    return graph.compile()


# Instancia global del orquestador compilado
orchestrator = build_orchestrator()


async def _save_ai_result_as_csv(
    tenant_id: str,
    task_id: str,
    category: str,
    filename: str,
    data: list[dict]
) -> None:
    """Exporta una lista de diccionarios a CSV y la registra en TenantDocument."""
    import csv
    import os
    import uuid
    from app.db.base import AsyncSessionLocal
    from app.db.models.models import TenantDocument

    if not data:
        return

    try:
        _THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        upload_dir = os.path.normpath(os.path.join(_THIS_DIR, "..", "uploads"))
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)

        keys = data[0].keys()
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(data)

        async with AsyncSessionLocal() as db:
            doc = TenantDocument(
                tenant_id=uuid.UUID(tenant_id),
                task_id=uuid.UUID(task_id),
                file_name=filename,
                file_path=file_path,
                file_type="text/csv",
                file_size=os.path.getsize(file_path),
                category=category,
                status="completed",
                parsed_content=f"Datos exportados para análisis: {len(data)} registros."
            )
            db.add(doc)
            await db.commit()
    except Exception as e:
        print(f"Error al exportar datos a CSV: {e}")
