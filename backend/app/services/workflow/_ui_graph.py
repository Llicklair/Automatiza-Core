"""Funciones de generacion de grafos UI (nodos/aristas ReactFlow) para workflows."""

from collections import defaultdict

# ── Constantes de mapeo ──────────────────────────────────────────────────────

_AGENT_TYPES = {
    "billing": "skill",
    "hr": "skill",
    "crm": "skill",
    "advisory": "skill",
    "banking": "skill",
    "documents": "skill",
    "compliance": "skill",
    "rag": "skill",
    "excel": "skill",
    "email": "skill",
    "coordinator": "action",
    "workflow": "action",
    "orchestrator": "action",
    "skill": "skill",
}

_AGENT_LABELS = {
    "billing": "Facturacion",
    "hr": "RRHH",
    "crm": "CRM",
    "advisory": "Asesoria Fiscal",
    "banking": "Banca",
    "documents": "Documentos",
    "compliance": "Cumplimiento",
    "rag": "Busqueda RAG",
    "excel": "Excel",
    "email": "Email",
    "coordinator": "Coordinador",
    "orchestrator": "Orquestador",
    "workflow": "Workflow",
}

_TRIGGER_LABELS = {
    "event_based": "Evento ERP",
    "schedule_based": "Programacion",
    "manual": "Inicio Manual",
}

_INSTRUCTION_TO_AGENT = [
    (["factura", "cobro", "pago", "billing", "invoice"], "billing", "Facturacion"),
    (["empleado", "nomina", "nomina", "rrhh", "salario", "hr"], "hr", "RRHH"),
    (["cliente", "crm", "venta", "oportunidad", "contacto"], "crm", "CRM"),
    (["fiscal", "impuesto", "iva", "irpf", "aeat", "advisory"], "advisory", "Asesoria Fiscal"),
    (["banco", "cuenta", "transferencia", "banking"], "banking", "Banca"),
    (["documento", "archivo", "ocr", "contrato", "pdf"], "documents", "Documentos"),
    (["email", "correo", "envia", "envia", "notifica"], "email", "Email"),
    (["excel", "hoja", "informe", "reporte"], "excel", "Excel / Informe"),
]

# Directivas específicas por dominio cuando el parser detecta varias skills y
# todas comparten la misma instrucción maestra. Sin esto cada agente recibe la
# misma orden literal y los que no son del dominio principal terminan
# rechazando la tarea o devolviendo respuestas incoherentes (ej. CRM intentando
# "extraer PDFs"). Cada directiva re-encuadra la sub-tarea para que el agente
# aporte SU especialidad al objetivo común.
_DOMAIN_DIRECTIVES = {
    "billing": (
        "Encárgate de la parte de facturación: lista facturas relevantes con "
        "número, cliente, importe, fechas, estado y días vencidos."
    ),
    "crm": (
        "Aporta contexto comercial sobre los clientes implicados: estado del "
        "lead/oportunidad, segmento, riesgo de churn y negociaciones en curso. "
        "NO intentes extraer datos de facturación — eso lo aporta otro agente."
    ),
    "email": (
        "Prepara el borrador de correo de comunicación con el contenido "
        "relevante para los destinatarios afectados (recordatorios, avisos, "
        "convocatorias). NO ejecutes acciones de otros dominios."
    ),
    "hr": (
        "Aporta el contexto de empleados afectados (nombres, departamentos, "
        "estado laboral). NO toques facturación ni operaciones de otros "
        "dominios."
    ),
    "banking": (
        "Cruza con movimientos bancarios para identificar cobros, transferencias "
        "o impagos relacionados con la consulta. NO intentes generar facturas."
    ),
    "excel": (
        "Genera la hoja Excel/CSV con los datos tabulados que el usuario pidió "
        "para esta tarea. Los datos provienen de otros agentes; tú formateas."
    ),
    "documents": (
        "Localiza los documentos relevantes en el gestor documental "
        "(contratos, PDFs, recibos) y devuelve resumen + referencias."
    ),
    "rag": (
        "Busca en la base de conocimiento del tenant referencias relevantes al "
        "asunto y devuelve citas o respuestas basadas en lo encontrado."
    ),
    "compliance": (
        "Verifica obligaciones fiscales/normativas relacionadas (modelos AEAT "
        "aplicables, vencimientos, riesgos)."
    ),
    "advisory": (
        "Aporta análisis fiscal-asesor: implicaciones impositivas, "
        "deducciones aplicables y recomendaciones."
    ),
    "report": (
        "Genera el informe ejecutivo con totales, alertas clave y próximos "
        "pasos accionables."
    ),
    "marketing": (
        "Prepara el contenido de marketing/comunicación pública relacionado."
    ),
    "recruitment": (
        "Aporta contexto de selección de personal (candidatos, vacantes)."
    ),
}


def _per_domain_instruction(agent: str, master: str, multi: bool) -> str:
    """Si hay múltiples skills compartiendo la misma instrucción maestra, devuelve
    una versión adaptada al dominio (directiva + contexto general). Si solo hay
    una skill, devuelve la instrucción original recortada — ese agente es el lead.
    """
    raw = (master or "").strip()
    if not multi:
        return raw[:200]
    directive = _DOMAIN_DIRECTIVES.get(agent)
    if not directive:
        return raw[:200]
    return f"{directive}\n\nContexto general de la tarea: {raw[:160]}"


# ── Funciones publicas ───────────────────────────────────────────────────────


def plan_to_ui_graph(plan: list, trigger_type: str) -> tuple[list, list]:
    """Convierte el plan del orquestador (lista de SubTask) en nodos y aristas ReactFlow."""
    nodes: list[dict] = []
    edges: list[dict] = []

    # Nodo trigger
    nodes.append(
        {
            "id": "trigger",
            "type": "trigger",
            "position": {"x": 250, "y": 0},
            "data": {
                "label": _TRIGGER_LABELS.get(trigger_type, "Trigger"),
                "trigger_type": trigger_type,
            },
        }
    )

    # Indice id -> posicion
    step_id_to_index: dict[str, int] = {}
    for i, step in enumerate(plan):
        step_id_to_index[step.get("id", f"step_{i}")] = i

    # Capas topologicas
    layers: dict[str, int] = {}
    for i, step in enumerate(plan):
        step_id = step.get("id", f"step_{i}")
        deps = step.get("depends_on", [])
        if not deps:
            layers[step_id] = 0
        else:
            layers[step_id] = max(layers.get(d, 0) for d in deps) + 1

    # Agrupar por capa y posicionar
    layer_groups: dict[int, list] = defaultdict(list)
    for i, step in enumerate(plan):
        step_id = step.get("id", f"step_{i}")
        layer_groups[layers.get(step_id, i)].append((i, step_id, step))

    COL_W, ROW_H = 220, 130
    for layer_idx in sorted(layer_groups.keys()):
        items = layer_groups[layer_idx]
        total_w = len(items) * COL_W
        start_x = 250 - total_w // 2 + COL_W // 2
        for col_idx, (_original_idx, step_id, step) in enumerate(items):
            agent = step.get("agent", step.get("domain", "skill"))
            nodes.append(
                {
                    "id": step_id,
                    "type": _AGENT_TYPES.get(agent, "skill"),
                    "position": {"x": start_x + col_idx * COL_W, "y": 150 + layer_idx * ROW_H},
                    "data": {
                        "label": _AGENT_LABELS.get(agent, agent.title()),
                        "domain": agent,
                        "description": step.get("action", step.get("instruction", ""))[:120],
                    },
                }
            )
            deps = step.get("depends_on", [])
            if deps:
                for dep_id in deps:
                    edges.append(
                        {"id": f"e-{dep_id}-{step_id}", "source": dep_id, "target": step_id}
                    )
            else:
                edges.append({"id": f"e-trigger-{step_id}", "source": "trigger", "target": step_id})

    return nodes, edges


def _pick_employee(domain: str, employees):
    """Devuelve el AIEmployee más adecuado para un dominio: custom > builtin.

    Si no hay AIEmployee disponible para ese dominio, devuelve None y el caller
    cae al label/domain genéricos.
    """
    if not employees:
        return None
    candidates = [e for e in employees if e.domain == domain]
    custom = next((e for e in candidates if not e.is_builtin), None)
    if custom is not None:
        return custom
    return next((e for e in candidates if e.is_builtin), None)


def _skill_data(
    default_label: str,
    agent: str,
    instruction: str,
    employees,
    *,
    multi: bool = False,
) -> dict:
    """Construye data de un skill node enriquecido con employee_id cuando hay AIEmployee.

    - Si el match es custom: domain="custom", label=<name>, employee_id=<uuid>.
    - Si es builtin: domain=<agent>, label=<name>, employee_id=<uuid>.
    - Sin match: domain=<agent>, label=<default_label>, sin employee_id.

    multi: cuando True (varias skills paralelas), la instrucción se reescribe
    con la directiva específica de dominio para evitar que cada agente reciba
    la orden maestra entera y la rechace.
    """
    final_instr = _per_domain_instruction(agent, instruction, multi)
    emp = _pick_employee(agent, employees or [])
    if emp is None:
        return {"label": default_label, "domain": agent, "instruction": final_instr}
    if not emp.is_builtin:
        return {
            "label": emp.name,
            "domain": "custom",
            "employee_id": str(emp.id),
            "instruction": final_instr,
        }
    return {
        "label": emp.name,
        "domain": agent,
        "employee_id": str(emp.id),
        "instruction": final_instr,
    }


def generate_preview_nodes(payload: dict, employees=None) -> tuple[list, list]:
    """Genera topologia visual minima a partir del payload parseado por IA.

    employees: lista opcional de AIEmployee del tenant. Cuando se pasa, cada
    skill node se etiqueta con el nombre real del agente (custom > builtin) y
    se inyecta data.employee_id para que el dispatcher pueda invocarlo.
    """
    trigger_type = payload.get("trigger_type", "manual")
    instruction = (payload.get("action_config") or {}).get("instruction", "")
    description = payload.get("description", "")
    text = (instruction + " " + description).lower()

    detected = []
    for keywords, agent, label in _INSTRUCTION_TO_AGENT:
        if any(kw in text for kw in keywords):
            detected.append((agent, label))
    if not detected:
        detected = [("skill", "Agente IA")]

    CENTER_X = 300
    nodes = [
        {
            "id": "trigger",
            "type": "trigger",
            "position": {"x": CENTER_X, "y": 0},
            "data": {
                "label": _TRIGGER_LABELS.get(trigger_type, "Trigger"),
                "trigger_type": trigger_type,
            },
        }
    ]
    edges = []

    if len(detected) <= 1:
        agent, label = detected[0]
        node_id = "preview_agent_0"
        nodes.append(
            {
                "id": node_id,
                "type": "skill",
                "position": {"x": CENTER_X, "y": 160},
                "data": _skill_data(label, agent, instruction, employees),
            }
        )
        edges.append({"id": f"e-trigger-{node_id}", "source": "trigger", "target": node_id})
    else:
        SPACING = 280
        total_width = (len(detected) - 1) * SPACING
        start_x = CENTER_X - total_width / 2
        branch_ids = []

        for i, (agent, label) in enumerate(detected):
            node_id = f"preview_{agent}_{i}"
            branch_ids.append(node_id)
            nodes.append(
                {
                    "id": node_id,
                    "type": "skill",
                    "position": {"x": int(start_x + i * SPACING), "y": 170},
                    "data": _skill_data(label, agent, instruction, employees, multi=True),
                }
            )
            edges.append({"id": f"e-trigger-{node_id}", "source": "trigger", "target": node_id})

        join_id = "preview_consolidar"
        consolidate_instr = (
            f"Genera un informe ejecutivo resumiendo el estado actual del negocio: "
            f"{instruction[:150]}. Incluye totales, alertas y proximos pasos."
        )
        nodes.append(
            {
                "id": join_id,
                "type": "skill",
                "position": {"x": CENTER_X, "y": 330},
                "data": _skill_data(
                    "Informe de resumen", "billing", consolidate_instr, employees
                ),
            }
        )
        for bid in branch_ids:
            edges.append({"id": f"e-{bid}-{join_id}", "source": bid, "target": join_id})

    return nodes, edges
