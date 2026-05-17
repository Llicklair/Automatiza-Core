"""HR agent package.

Public API: the compiled ``graph`` plus the individual ``@tool`` functions
consumed by ``app.agents.tool_registry``. Internal nodes and the ``tools``
list are intentionally NOT re-exported (CLAUDE.md agent boundary).
"""

from .agent import graph
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
    "approve_payroll",
    "calculate_and_create_payroll",
    "create_employee",
    "generate_all_payrolls",
    "list_employees",
    "list_payrolls",
    "update_payroll",
]
