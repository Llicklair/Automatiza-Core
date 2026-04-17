"""HR agent — payroll tools re-export facade.

Logic lives in:
  _payroll_pdf.py   — PDF generation helper
  _payroll_calc.py  — calculate_and_create_payroll, generate_all_payrolls
  _payroll_crud.py  — update_payroll, approve_payroll, list_payrolls
"""

from app.agents.hr._payroll_pdf import _generate_and_save_payroll_pdf  # noqa: F401
from app.agents.hr._payroll_calc import (  # noqa: F401
    calculate_and_create_payroll,
    generate_all_payrolls,
)
from app.agents.hr._payroll_crud import (  # noqa: F401
    update_payroll,
    approve_payroll,
    list_payrolls,
)

__all__ = [
    "_generate_and_save_payroll_pdf",
    "calculate_and_create_payroll",
    "generate_all_payrolls",
    "update_payroll",
    "approve_payroll",
    "list_payrolls",
]
