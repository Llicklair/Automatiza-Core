"""Tool de propuesta y aplicación de horarios de trabajo (gateada por autonomía)."""

import logging
import re
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models.hr import LeaveRequest
from app.db.models.models import Employee
from app.services.autonomy_gate import gated_tool

logger = logging.getLogger(__name__)

_TIME_RE = re.compile(r"^\d{2}:\d{2}$")


def _summary(kwargs: dict) -> str:
    n = len(kwargs.get("schedules") or [])
    return f"Aplicar horario semanal propuesto a {n} empleado(s)"


@tool
@gated_tool(domain="hr", summary_fn=_summary)
async def propose_schedule(
    tenant_id: str,
    schedules: list[dict],
    rationale: Optional[str] = None,
) -> str:
    """Propone y aplica horarios semanales de trabajo para uno o varios empleados.
    La aplicación requiere aprobación humana según el nivel de autonomía configurado.
    Args:
        tenant_id: ID del tenant
        schedules: Lista de horarios por empleado. Cada item:
            {"employee_id": "<uuid>", "days": [{"day_of_week": 0-6 (0=lunes),
            "start_time": "HH:MM", "end_time": "HH:MM"}, ...]}
        rationale: Justificación breve de la propuesta (cobertura, vacaciones, etc.)
    """
    from app.services.hr.commands import upsert_schedule

    if not schedules:
        return "Error: la lista de horarios está vacía."
    for item in schedules:
        if "employee_id" not in item or not item.get("days"):
            return "Error: cada item necesita employee_id y days (lista no vacía)."
        for d in item["days"]:
            if d.get("day_of_week") not in range(7):
                return f"Error: day_of_week inválido en {item['employee_id']}: {d.get('day_of_week')} (0=lunes..6=domingo)."
            for k in ("start_time", "end_time"):
                if not _TIME_RE.match(str(d.get(k, ""))):
                    return f"Error: {k} inválido en {item['employee_id']}: '{d.get(k)}' (formato HH:MM)."

    emp_ids = [UUID(str(s["employee_id"])) for s in schedules]
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(Employee.id, Employee.name).where(
                Employee.tenant_id == UUID(tenant_id), Employee.id.in_(emp_ids)
            )
        )
        found = {row.id: row.name for row in res.all()}
        missing = [str(e) for e in emp_ids if e not in found]
        if missing:
            return f"Error: empleados no encontrados en el tenant: {', '.join(missing)}"

        # Avisos por ausencias aprobadas en los próximos 7 días (no bloquea)
        today = date.today()
        leaves_res = await db.execute(
            select(LeaveRequest.employee_id, LeaveRequest.leave_type).where(
                LeaveRequest.tenant_id == UUID(tenant_id),
                LeaveRequest.employee_id.in_(emp_ids),
                LeaveRequest.status == "approved",
                LeaveRequest.start_date <= today + timedelta(days=7),
                LeaveRequest.end_date >= today,
            )
        )
        warnings = [
            f"{found[eid]} tiene una ausencia aprobada ({ltype}) en los próximos 7 días"
            for eid, ltype in leaves_res.all()
        ]

        applied = []
        for item in schedules:
            eid = UUID(str(item["employee_id"]))
            rows = await upsert_schedule(
                db,
                UUID(tenant_id),
                eid,
                [
                    {
                        "day_of_week": d["day_of_week"],
                        "start_time": d["start_time"],
                        "end_time": d["end_time"],
                        "active": True,
                    }
                    for d in item["days"]
                ],
            )
            applied.append(f"{found[eid]}: {len(rows)} día(s)")

    msg = "Horario aplicado:\n- " + "\n- ".join(applied)
    if rationale:
        msg += f"\nJustificación: {rationale}"
    if warnings:
        msg += "\nAvisos:\n- " + "\n- ".join(warnings)
    return msg
