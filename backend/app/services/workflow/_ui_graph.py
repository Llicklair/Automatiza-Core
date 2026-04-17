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


# ── Funciones publicas ───────────────────────────────────────────────────────


def plan_to_ui_graph(plan: list, trigger_type: str) -> tuple[list, list]:
    """Convierte el plan del orquestador (lista de SubTask) en nodos y aristas ReactFlow."""
    nodes: list[dict] = []
    edges: list[dict] = []

    # Nodo trigger
    nodes.append({
        "id": "trigger",
        "type": "trigger",
        "position": {"x": 250, "y": 0},
        "data": {
            "label": _TRIGGER_LABELS.get(trigger_type, "Trigger"),
            "trigger_type": trigger_type,
        },
    })

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
            nodes.append({
                "id": step_id,
                "type": _AGENT_TYPES.get(agent, "skill"),
                "position": {"x": start_x + col_idx * COL_W, "y": 150 + layer_idx * ROW_H},
                "data": {
                    "label": _AGENT_LABELS.get(agent, agent.title()),
                    "domain": agent,
                    "description": step.get("action", step.get("instruction", ""))[:120],
                },
            })
            deps = step.get("depends_on", [])
            if deps:
                for dep_id in deps:
                    edges.append({"id": f"e-{dep_id}-{step_id}", "source": dep_id, "target": step_id})
            else:
                edges.append({"id": f"e-trigger-{step_id}", "source": "trigger", "target": step_id})

    return nodes, edges


def generate_preview_nodes(payload: dict) -> tuple[list, list]:
    """Genera topologia visual minima a partir del payload parseado por IA."""
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
    nodes = [{
        "id": "trigger", "type": "trigger",
        "position": {"x": CENTER_X, "y": 0},
        "data": {"label": _TRIGGER_LABELS.get(trigger_type, "Trigger"), "trigger_type": trigger_type},
    }]
    edges = []

    if len(detected) <= 1:
        agent, label = detected[0]
        node_id = "preview_agent_0"
        nodes.append({
            "id": node_id, "type": "skill",
            "position": {"x": CENTER_X, "y": 160},
            "data": {"label": label, "domain": agent, "instruction": instruction[:200]},
        })
        edges.append({"id": f"e-trigger-{node_id}", "source": "trigger", "target": node_id})
    else:
        SPACING = 280
        total_width = (len(detected) - 1) * SPACING
        start_x = CENTER_X - total_width / 2
        branch_ids = []

        for i, (agent, label) in enumerate(detected):
            node_id = f"preview_{agent}_{i}"
            branch_ids.append(node_id)
            nodes.append({
                "id": node_id, "type": "skill",
                "position": {"x": int(start_x + i * SPACING), "y": 170},
                "data": {"label": label, "domain": agent, "instruction": instruction[:200]},
            })
            edges.append({"id": f"e-trigger-{node_id}", "source": "trigger", "target": node_id})

        join_id = "preview_consolidar"
        nodes.append({
            "id": join_id, "type": "skill",
            "position": {"x": CENTER_X, "y": 330},
            "data": {
                "label": "Informe de resumen", "domain": "billing",
                "instruction": f"Genera un informe ejecutivo resumiendo el estado actual del negocio: {instruction[:150]}. Incluye totales, alertas y proximos pasos.",
            },
        })
        for bid in branch_ids:
            edges.append({"id": f"e-{bid}-{join_id}", "source": bid, "target": join_id})

    return nodes, edges
