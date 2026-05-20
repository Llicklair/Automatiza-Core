"""Tests para app.services.workflow._ui_graph.

Cobertura de la generación de grafos UI (ReactFlow) para preview de workflows.
Lógica pura sin DB ni LLM — fácil de testear; pre-iteración solo 8%.
"""

from types import SimpleNamespace
from uuid import uuid4

from app.services.workflow._ui_graph import (
    _DOMAIN_DIRECTIVES,
    _per_domain_instruction,
    _pick_employee,
    _skill_data,
    generate_preview_nodes,
    plan_to_ui_graph,
)


def _emp(domain, name="X", is_builtin=True):
    """Stub mínimo de AIEmployee para los helpers (no toca DB)."""
    return SimpleNamespace(
        id=uuid4(), domain=domain, name=name, is_builtin=is_builtin
    )


# ── _per_domain_instruction ──────────────────────────────────────────────────


class TestPerDomainInstruction:
    def test_single_skill_devuelve_instruccion_recortada(self):
        master = "x" * 500
        result = _per_domain_instruction("billing", master, multi=False)
        assert len(result) == 200
        assert result == "x" * 200

    def test_multi_con_dominio_conocido_usa_directiva(self):
        result = _per_domain_instruction("crm", "Recordatorio impagos", multi=True)
        # La directiva CRM aparece y la maestra queda como contexto
        assert "contexto comercial" in result.lower()
        assert "Recordatorio impagos" in result

    def test_multi_con_dominio_desconocido_fallback_a_recorte(self):
        result = _per_domain_instruction("dominio_inexistente", "abc", multi=True)
        assert result == "abc"

    def test_master_None_single_devuelve_string_vacio(self):
        """Single + master None: nada que recortar."""
        assert _per_domain_instruction("billing", None, multi=False) == ""

    def test_master_None_multi_aplica_directiva_aunque_no_haya_contexto(self):
        """Multi + dominio conocido: aplica la directiva aunque master esté vacío.
        El agente recibe la directiva (sabe qué aportar) pero sin contexto."""
        result = _per_domain_instruction("crm", None, multi=True)
        assert "contexto comercial" in result.lower()
        assert result.rstrip().endswith("Contexto general de la tarea:")

    def test_master_vacio_multi_sin_dominio_devuelve_vacio(self):
        """Multi + dominio desconocido + master vacío: nada que devolver."""
        result = _per_domain_instruction("dominio_desconocido", "", multi=True)
        assert result == ""

    def test_todas_las_directivas_existen(self):
        """Documenta los dominios soportados — guard contra olvidar añadir uno."""
        expected = {"billing", "crm", "email", "hr", "banking", "excel",
                    "documents", "rag", "compliance", "advisory", "report",
                    "marketing", "recruitment"}
        assert expected.issubset(set(_DOMAIN_DIRECTIVES.keys()))


# ── plan_to_ui_graph ─────────────────────────────────────────────────────────


class TestPlanToUiGraph:
    def test_plan_vacio_devuelve_solo_trigger(self):
        nodes, edges = plan_to_ui_graph([], "manual")
        assert len(nodes) == 1
        assert nodes[0]["id"] == "trigger"
        assert nodes[0]["data"]["trigger_type"] == "manual"
        assert edges == []

    def test_single_step_genera_trigger_y_step_conectados(self):
        plan = [{"id": "s1", "agent": "billing", "action": "Lista facturas"}]
        nodes, edges = plan_to_ui_graph(plan, "manual")
        ids = [n["id"] for n in nodes]
        assert "trigger" in ids and "s1" in ids
        # Edge trigger -> s1
        assert any(e["source"] == "trigger" and e["target"] == "s1" for e in edges)

    def test_step_sin_deps_se_conecta_a_trigger(self):
        plan = [
            {"id": "a", "agent": "billing"},
            {"id": "b", "agent": "crm"},
        ]
        _, edges = plan_to_ui_graph(plan, "manual")
        # Ambos sin deps → ambos conectan a trigger
        sources = [e["source"] for e in edges]
        assert sources.count("trigger") == 2

    def test_dependencias_se_traducen_en_edges(self):
        plan = [
            {"id": "a", "agent": "billing"},
            {"id": "b", "agent": "crm", "depends_on": ["a"]},
        ]
        _, edges = plan_to_ui_graph(plan, "manual")
        assert any(e["source"] == "a" and e["target"] == "b" for e in edges)
        # b NO se conecta a trigger (tiene dep)
        b_edges = [e for e in edges if e["target"] == "b"]
        assert all(e["source"] != "trigger" for e in b_edges)

    def test_capas_topologicas_posicionan_y_correctamente(self):
        """Step con depends_on debería tener y mayor que su dependencia."""
        plan = [
            {"id": "a", "agent": "billing"},
            {"id": "b", "agent": "crm", "depends_on": ["a"]},
            {"id": "c", "agent": "email", "depends_on": ["b"]},
        ]
        nodes, _ = plan_to_ui_graph(plan, "manual")
        y_by_id = {n["id"]: n["position"]["y"] for n in nodes}
        assert y_by_id["a"] < y_by_id["b"] < y_by_id["c"]

    def test_trigger_label_se_resuelve(self):
        nodes_event, _ = plan_to_ui_graph([], "event_based")
        nodes_sched, _ = plan_to_ui_graph([], "schedule_based")
        nodes_unk, _ = plan_to_ui_graph([], "unknown_trigger_xyz")
        assert "Evento" in nodes_event[0]["data"]["label"]
        assert "Programacion" in nodes_sched[0]["data"]["label"]
        # Fallback genérico para trigger desconocido
        assert nodes_unk[0]["data"]["label"] == "Trigger"

    def test_agent_desconocido_usa_titlecase_de_fallback(self):
        plan = [{"id": "s1", "agent": "agente_raro_nuevo"}]
        nodes, _ = plan_to_ui_graph(plan, "manual")
        s1 = next(n for n in nodes if n["id"] == "s1")
        # Label cae al .title() del agent name
        assert s1["data"]["label"] == "Agente_Raro_Nuevo"

    def test_description_se_recorta_a_120(self):
        plan = [{"id": "s1", "agent": "billing", "action": "x" * 500}]
        nodes, _ = plan_to_ui_graph(plan, "manual")
        s1 = next(n for n in nodes if n["id"] == "s1")
        assert len(s1["data"]["description"]) == 120


# ── _pick_employee ───────────────────────────────────────────────────────────


class TestPickEmployee:
    def test_lista_vacia_devuelve_None(self):
        assert _pick_employee("billing", []) is None
        assert _pick_employee("billing", None) is None

    def test_custom_gana_sobre_builtin(self):
        builtin = _emp("billing", "Builtin", is_builtin=True)
        custom = _emp("billing", "Custom", is_builtin=False)
        result = _pick_employee("billing", [builtin, custom])
        assert result is custom

    def test_solo_builtin_se_devuelve(self):
        builtin = _emp("billing", "Builtin", is_builtin=True)
        result = _pick_employee("billing", [builtin])
        assert result is builtin

    def test_sin_match_de_dominio_devuelve_None(self):
        emp = _emp("hr", "Alguien")
        assert _pick_employee("billing", [emp]) is None


# ── _skill_data ──────────────────────────────────────────────────────────────


class TestSkillData:
    def test_sin_employees_usa_default_label(self):
        data = _skill_data("Facturacion", "billing", "hazlo", [])
        assert data["label"] == "Facturacion"
        assert data["domain"] == "billing"
        assert "employee_id" not in data
        assert data["instruction"] == "hazlo"

    def test_con_custom_etiqueta_domain_custom(self):
        custom = _emp("billing", "Pepe CFO", is_builtin=False)
        data = _skill_data("Facturacion", "billing", "hazlo", [custom])
        assert data["domain"] == "custom"
        assert data["label"] == "Pepe CFO"
        assert data["employee_id"] == str(custom.id)

    def test_con_builtin_mantiene_domain_pero_label_real(self):
        builtin = _emp("billing", "Sara Builtin", is_builtin=True)
        data = _skill_data("Facturacion", "billing", "hazlo", [builtin])
        assert data["domain"] == "billing"  # NO "custom"
        assert data["label"] == "Sara Builtin"
        assert data["employee_id"] == str(builtin.id)

    def test_multi_aplica_directiva_por_dominio(self):
        data = _skill_data("CRM", "crm", "Recordatorio impagos", [], multi=True)
        # La directiva CRM debe aparecer (no la instrucción literal sola)
        assert "contexto comercial" in data["instruction"].lower()

    def test_employees_None_no_crashea(self):
        data = _skill_data("X", "billing", "i", None)
        assert "employee_id" not in data


# ── generate_preview_nodes ───────────────────────────────────────────────────


class TestGeneratePreviewNodes:
    def test_payload_minimo_genera_trigger_y_un_skill(self):
        payload = {
            "trigger_type": "manual",
            "action_config": {"instruction": "envía un email de bienvenida"},
        }
        nodes, edges = generate_preview_nodes(payload)
        ids = [n["id"] for n in nodes]
        assert "trigger" in ids
        # Hay UN agent node (email detectado)
        agent_nodes = [n for n in nodes if n["type"] == "skill"]
        assert len(agent_nodes) == 1
        assert agent_nodes[0]["data"]["domain"] == "email"

    def test_sin_keywords_detectadas_fallback_a_skill_generico(self):
        payload = {
            "trigger_type": "manual",
            "action_config": {"instruction": "hazme algo abstracto sin keywords"},
        }
        nodes, _ = generate_preview_nodes(payload)
        agent_nodes = [n for n in nodes if n["type"] == "skill"]
        assert len(agent_nodes) == 1
        assert agent_nodes[0]["data"]["label"] == "Agente IA"

    def test_multi_dominio_anyade_consolidacion(self):
        payload = {
            "trigger_type": "manual",
            "action_config": {
                "instruction": "factura impagas + cliente segmento + email recordatorio"
            },
        }
        nodes, edges = generate_preview_nodes(payload)
        # billing + crm + email detectados → 3 branches + consolidate
        skill_nodes = [n for n in nodes if n["type"] == "skill"]
        assert len(skill_nodes) >= 4  # 3 detected + consolidate
        # Edge de consolidación: las branches apuntan al join
        join_id = "preview_consolidar"
        join_edges = [e for e in edges if e["target"] == join_id]
        assert len(join_edges) >= 2

    def test_employees_se_inyectan_en_skill_nodes(self):
        emp = _emp("email", "Lucía Email", is_builtin=True)
        payload = {
            "trigger_type": "manual",
            "action_config": {"instruction": "envía email"},
        }
        nodes, _ = generate_preview_nodes(payload, employees=[emp])
        skill = next(n for n in nodes if n["type"] == "skill")
        assert skill["data"]["label"] == "Lucía Email"
        assert skill["data"]["employee_id"] == str(emp.id)

    def test_trigger_type_event_based(self):
        payload = {"trigger_type": "event_based", "action_config": {"instruction": "fact"}}
        nodes, _ = generate_preview_nodes(payload)
        trigger = next(n for n in nodes if n["id"] == "trigger")
        assert trigger["data"]["trigger_type"] == "event_based"

    def test_description_se_concatena_a_instruction_para_detectar(self):
        """Si action_config.instruction no tiene keywords pero description sí, detecta."""
        payload = {
            "trigger_type": "manual",
            "description": "Procesa facturas",
            "action_config": {"instruction": "abstract task"},
        }
        nodes, _ = generate_preview_nodes(payload)
        billing_node = [n for n in nodes if n.get("data", {}).get("domain") == "billing"]
        assert billing_node, "billing debería detectarse vía description"

    def test_action_config_None_no_crashea(self):
        payload = {"trigger_type": "manual", "description": "fact"}
        nodes, _ = generate_preview_nodes(payload)
        assert len(nodes) >= 2
