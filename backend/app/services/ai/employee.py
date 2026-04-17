"""Servicio de dominio para empleados IA.

Re-exporta desde los sub-módulos:
  - employee_crud: CRUD, skills catalog, activity feed, instrucciones directas
  - employee_provisioning: seed built-in, provisioning LLM en background
"""

from app.services.ai.employee_crud import (
    AVAILABLE_SKILLS,
    create_activity,
    create_employee,
    delete_employee,
    instruct_employee,
    list_activity,
    list_employees,
    provision_employee,
    to_out,
    update_appearance,
    update_icon,
    update_status,
)
from app.services.ai.employee_provisioning import (
    provision_employee_bg,
    seed_builtin,
)

__all__ = [
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
]
