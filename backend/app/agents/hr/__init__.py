"""HR agent package — re-exports for backward compatibility."""

from .agent import graph, hr_agent_node, hr_finalize_node, tools
from .tools import (
    approve_payroll,
    calculate_and_create_payroll,
    create_employee,
    generate_all_payrolls,
    list_employees,
    list_payrolls,
    update_payroll,
)

__all__ = [
    "graph",
    "hr_agent_node",
    "hr_finalize_node",
    "tools",
    "approve_payroll",
    "calculate_and_create_payroll",
    "create_employee",
    "generate_all_payrolls",
    "list_employees",
    "list_payrolls",
    "update_payroll",
]
