"""Servicios de IA — dominio ai.

Re-exports de los módulos del dominio para importación conveniente.
"""

from app.services.ai.condition_evaluator import _resolve_field, evaluate_condition
# AI.SCO — `score_candidate` no se re-exporta en MVP. Función queda definida
# en cv_parser.py para reintroducción v1.2 con full compliance Anexo III AI Act
# (QMS, marcado CE, registro UE). Ver docs/ai_act_scoping.md.
from app.services.ai.cv_parser import extract_cv_data, parse_cv_file
from app.services.ai.employee import (
    AVAILABLE_SKILLS,
    create_activity,
    create_employee,
    delete_employee,
    instruct_employee,
    list_activity,
    list_employees,
    provision_employee,
    provision_employee_bg,
    seed_builtin,
    to_out,
    update_appearance,
    update_icon,
    update_status,
)
from app.services.ai.generative_ui import (
    debug_llm,
    delete_ui,
    fetch_erp_context,
    generate_ui,
    get_ui,
    list_uis,
    update_ui,
)
from app.services.ai.node_engine import NodeEngine
from app.services.ai.node_graph_helpers import has_advanced_nodes  # noqa: F401

__all__ = [
    # condition_evaluator
    "evaluate_condition",
    "_resolve_field",
    # cv_parser (score_candidate retirado en MVP — ver docs/ai_act_scoping.md)
    "extract_cv_data",
    "parse_cv_file",
    # employee
    "AVAILABLE_SKILLS",
    "create_activity",
    "create_employee",
    "delete_employee",
    "instruct_employee",
    "list_activity",
    "list_employees",
    "provision_employee",
    "provision_employee_bg",
    "seed_builtin",
    "to_out",
    "update_appearance",
    "update_icon",
    "update_status",
    # generative_ui
    "debug_llm",
    "delete_ui",
    "fetch_erp_context",
    "generate_ui",
    "get_ui",
    "list_uis",
    "update_ui",
    # node_engine
    "NodeEngine",
    "has_advanced_nodes",
]
