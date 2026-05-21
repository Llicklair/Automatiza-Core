"""Audit del contrato del AIEmployee custom sobre la BD actual.

Lista los empleados `is_builtin=False` por tenant y los clasifica según
las capacidades que declaran:

  - PASA el contrato (≥2 de 4)  → ningún cambio.
  - NO pasa el contrato         → candidato a degradar a "Perfil" (sólo
                                  system prompt). El frontend mostrará
                                  el aviso al admin del tenant al
                                  reabrir el empleado.

Este script no modifica datos: imprime el plan que un admin debe revisar
antes de ejecutar la data-migration definitiva.

Uso:
  py -3 backend/scripts/audit_aiemployees_contract.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Permitir ejecutar como script standalone.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.db.base import AsyncSessionLocal  # noqa: E402
from app.db.models.ai_employees import AIEmployee  # noqa: E402
from app.services.ai.employee_contract import (  # noqa: E402
    count_capabilities,
    validate_employee_contract,
)


async def main() -> int:
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(AIEmployee).where(AIEmployee.is_builtin.is_(False)).order_by(
                AIEmployee.tenant_id, AIEmployee.created_at
            )
        )
        rows = res.scalars().all()

    if not rows:
        print("Sin empleados custom en la BD. Nada que auditar.")
        return 0

    fails: list[tuple[AIEmployee, str]] = []
    passes: list[tuple[AIEmployee, int]] = []
    for emp in rows:
        n = count_capabilities(
            scope=emp.scope,
            memory_enabled=emp.memory_enabled,
            knowledge_enabled=emp.knowledge_enabled,
            workflows=emp.workflows,
        )
        ok, msg = validate_employee_contract(
            scope=emp.scope,
            memory_enabled=emp.memory_enabled,
            knowledge_enabled=emp.knowledge_enabled,
            workflows=emp.workflows,
        )
        if ok:
            passes.append((emp, n))
        else:
            fails.append((emp, msg))

    print(f"Empleados custom analizados: {len(rows)}")
    print(f"  - Cumplen contrato (>= 2/4): {len(passes)}")
    print(f"  - Sugieren degradar a Perfil: {len(fails)}")

    if passes:
        print("\nOK:")
        for emp, n in passes:
            print(f"  [{n}/4] tenant={emp.tenant_id}  {emp.name} ({emp.role})  id={emp.id}")

    if fails:
        print("\nDEGRADAR A PERFIL:")
        for emp, _msg in fails:
            print(f"        tenant={emp.tenant_id}  {emp.name} ({emp.role})  id={emp.id}")
        print(
            "\nSiguiente paso: revisar con el admin del tenant si quiere "
            "activar capacidades reales (scope/memory/knowledge/workflows) "
            "o convertir el empleado en un 'Perfil' (sólo system prompt)."
        )

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
