"""Rutas RRHH — agregador de los submódulos HR.

Los endpoints viven en:
- hr_employees.py  → empleados, documentos de empleado y documentos PDF HR
- hr_payrolls.py   → nóminas
- hr_time.py       → horarios, fichajes y ausencias
- hr_expenses.py   → gastos
"""

from fastapi import APIRouter

from app.api.v1.routes import hr_employees, hr_expenses, hr_payrolls, hr_time

router = APIRouter(prefix="/hr", tags=["hr"])

router.include_router(hr_employees.router)
router.include_router(hr_payrolls.router)
router.include_router(hr_time.router)
router.include_router(hr_expenses.router)
