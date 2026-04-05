"""
Herramienta para crear empleados IA desde descripción en lenguaje natural.
El LLM genera nombre, rol, dominio, system_prompt y skills automáticamente.
"""
import json
import logging
import uuid
from uuid import UUID

from langchain_core.tools import tool

from app.db.models.ai_employees import AIEmployee, AgentSkill
from app.agents.agent_tools import get_sync_db

logger = logging.getLogger(__name__)

AVAILABLE_SKILLS = [
    "billing.create_invoice", "billing.list_invoices", "billing.send_reminder",
    "hr.list_employees", "hr.generate_payroll", "hr.generate_document",
    "crm.list_clients", "crm.create_activity",
    "email.send", "email.read_inbox",
    "documents.search_rag", "documents.upload",
    "banking.list_transactions", "compliance.check", "excel.export",
]

VALID_EMPLOYEE_DOMAINS = {
    "billing", "documents", "compliance", "hr", "banking",
    "crm", "excel", "email", "marketing", "recruitment",
}

SPEC_PROMPT = """\
Eres el diseñador de agentes IA para AutomatizaPyme, una plataforma de gestión empresarial española.
Genera la especificación JSON de un nuevo empleado IA a partir de esta petición:

"{description}"

DOMINIOS válidos: {domains}
SKILLS disponibles: {skills}

Devuelve ÚNICAMENTE un JSON con estas claves:
- "name": nombre español realista (nombre + apellido), ej: "Laura Méndez"
- "role": cargo profesional en español, ej: "Directora de Marketing"
- "domain": uno de los dominios válidos que mejor represente la función
- "system_prompt": instrucciones detalladas en español (mínimo 3 frases). Incluye qué hace el agente, cómo debe comportarse y qué resultados debe producir.
- "skills": lista de tool_modules del catálogo relevantes para este dominio
- "budget_limit_usd": 10.0 por defecto

SOLO JSON, sin explicaciones."""


@tool
def create_ai_employee_from_description(tenant_id: str, description: str) -> str:
    """
    Crea un nuevo empleado IA a partir de una descripción en lenguaje natural.
    Usa LLM para generar nombre, rol, dominio, system_prompt y skills apropiados.
    Args:
        tenant_id: ID del tenant
        description: Descripción en lenguaje natural del empleado deseado
    """
    from app.core.llm_factory import get_llm

    # 1. Generar spec via LLM
    llm = get_llm(temperature=0.7)
    prompt = SPEC_PROMPT.format(
        description=description,
        domains=", ".join(sorted(VALID_EMPLOYEE_DOMAINS)),
        skills=", ".join(AVAILABLE_SKILLS),
    )

    try:
        response = llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        # Limpiar markdown fences si las hay
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        spec = json.loads(text.strip())
    except Exception as e:
        return f"Error generando especificación del empleado: {e}"

    # 2. Validar y normalizar
    name = spec.get("name", "Agente IA")
    role = spec.get("role", "Asistente")
    domain = spec.get("domain", "marketing")
    if domain not in VALID_EMPLOYEE_DOMAINS:
        domain = "marketing"
    system_prompt = spec.get("system_prompt", f"Soy {name}, {role}.")
    budget = float(spec.get("budget_limit_usd", 10.0))
    skills = [s for s in spec.get("skills", []) if s in AVAILABLE_SKILLS]

    # 3. Crear en BD
    try:
        with get_sync_db() as db:
            employee = AIEmployee(
                id=uuid.uuid4(),
                tenant_id=UUID(tenant_id),
                name=name,
                role=role,
                domain=domain,
                system_prompt=system_prompt,
                budget_limit_usd=budget,
                status="idle",
                is_builtin=False,
            )
            db.add(employee)
            db.flush()

            for skill_module in skills:
                db.add(AgentSkill(employee_id=employee.id, tool_module=skill_module))

            db.commit()

            skills_text = ", ".join(skills) if skills else "ninguna asignada"
            return (
                f"Empleado IA creado correctamente:\n"
                f"- Nombre: {name}\n"
                f"- Rol: {role}\n"
                f"- Dominio: {domain}\n"
                f"- Skills: {skills_text}\n"
                f"- ID: {employee.id}"
            )
    except Exception as e:
        return f"Error creando empleado IA en base de datos: {e}"
