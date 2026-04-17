"""
HR agent — tool functions re-export facade.

Implementation is split into focused sub-modules:
  _employee_tools.py — list_employees, create_employee
  _payroll_tools.py  — calculate_and_create_payroll, generate_all_payrolls,
                       update_payroll, approve_payroll, list_payrolls
"""

from app.agents.hr._employee_tools import create_employee, list_employees
from app.agents.hr._payroll_tools import (
    approve_payroll,
    calculate_and_create_payroll,
    generate_all_payrolls,
    list_payrolls,
    update_payroll,
)

__all__ = [
    "list_employees",
    "create_employee",
    "calculate_and_create_payroll",
    "generate_all_payrolls",
    "update_payroll",
    "approve_payroll",
    "list_payrolls",
]
