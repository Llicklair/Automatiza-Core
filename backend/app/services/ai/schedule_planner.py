"""
Generador de horarios semanales con IA.

Recibe un listado de empleados y una instrucción en lenguaje natural,
devuelve una propuesta de grid horario por empleado (lun-dom).
"""

import json
import logging
from typing import Any

from app.core.llm_factory import get_llm

logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = """Eres un asistente de RRHH especializado en planificar horarios laborales.
Recibes una lista de empleados y una instrucción del responsable.
Devuelves UN ÚNICO JSON con la propuesta de horario semanal de cada empleado.

Convenciones obligatorias:
- day_of_week: 0=Lunes, 1=Martes, 2=Miércoles, 3=Jueves, 4=Viernes, 5=Sábado, 6=Domingo
- start_time / end_time en formato "HH:MM" 24h
- active=true significa que ese día trabaja; active=false significa libranza
- Si la instrucción no menciona un empleado por nombre, aplica el horario a todos

Formato de respuesta (sin texto adicional, solo JSON):
{
  "suggestions": [
    {
      "employee_id": "<uuid del empleado>",
      "schedule": {
        "0": {"start_time": "09:00", "end_time": "17:00", "active": true},
        "1": {"start_time": "09:00", "end_time": "17:00", "active": true},
        "2": {"start_time": "09:00", "end_time": "17:00", "active": true},
        "3": {"start_time": "09:00", "end_time": "17:00", "active": true},
        "4": {"start_time": "09:00", "end_time": "15:00", "active": true},
        "5": {"start_time": "09:00", "end_time": "17:00", "active": false},
        "6": {"start_time": "09:00", "end_time": "17:00", "active": false}
      }
    }
  ],
  "rationale": "Breve explicación en español de la decisión tomada (1-2 frases)."
}

Reglas:
- Devuelve SIEMPRE las 7 claves 0..6 en cada schedule, aunque el día sea libranza.
- No inventes IDs: usa solo los que aparecen en la lista de empleados.
- Si la instrucción es ambigua, elige la interpretación más razonable y explícala en rationale.
"""


async def suggest_schedules(
    employees: list[dict[str, Any]],
    instruction: str,
) -> dict[str, Any]:
    """
    Genera una propuesta de horarios para un grupo de empleados.

    Args:
        employees: lista de dicts con keys: id, name, role, department.
        instruction: texto del responsable (ej. "todos de 9 a 18 lunes a viernes").

    Returns:
        dict con keys:
          - suggestions: lista de {employee_id, schedule: {0..6: DaySchedule}}
          - rationale: str
    """
    from langchain_core.messages import HumanMessage, SystemMessage

    if not employees:
        return {"suggestions": [], "rationale": "No hay empleados activos."}

    emp_lines = "\n".join(
        f"- id={e['id']} | nombre={e.get('name', '?')}"
        f" | rol={e.get('role') or '—'} | depto={e.get('department') or '—'}"
        for e in employees
    )

    user_content = (
        f"Empleados disponibles:\n{emp_lines}\n\n"
        f"Instrucción del responsable:\n{instruction.strip()}"
    )

    llm = get_llm(temperature=0)
    response = await llm.ainvoke(
        [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ]
    )

    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("schedule_planner: JSON inválido devuelto por el LLM")
        return {"suggestions": [], "rationale": "No se pudo interpretar la respuesta del modelo."}

    suggestions = data.get("suggestions") or []
    valid_ids = {str(e["id"]) for e in employees}
    cleaned: list[dict[str, Any]] = []
    for s in suggestions:
        emp_id = str(s.get("employee_id", "")).strip()
        if emp_id not in valid_ids:
            continue
        schedule = s.get("schedule") or {}
        normalized: dict[str, dict[str, Any]] = {}
        for day in range(7):
            entry = schedule.get(str(day)) or schedule.get(day) or {}
            normalized[str(day)] = {
                "start_time": str(entry.get("start_time") or "09:00"),
                "end_time": str(entry.get("end_time") or "17:00"),
                "active": bool(entry.get("active", False)),
            }
        cleaned.append({"employee_id": emp_id, "schedule": normalized})

    return {
        "suggestions": cleaned,
        "rationale": str(data.get("rationale") or "").strip(),
    }
