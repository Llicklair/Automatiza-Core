"""
Herramienta para crear empleados IA desde descripción en lenguaje natural.
El LLM genera nombre, rol, dominio, system_prompt y skills automáticamente.
"""

import json
import logging
import uuid
from uuid import UUID

from langchain_core.tools import tool

from app.core.llm_factory import get_llm
from app.db.base import AsyncSessionLocal
from app.db.models.ai_employees import AgentSkill, AIEmployee

logger = logging.getLogger(__name__)

AVAILABLE_SKILLS = [
    # billing
    "billing.create_invoice",
    "billing.list_invoices",
    "billing.update_invoice",
    "billing.update_invoice_status",
    "billing.search_client",
    "billing.send_invoice_by_email",
    # hr
    "hr.list_employees",
    "hr.create_employee",
    "hr.calculate_and_create_payroll",
    "hr.generate_all_payrolls",
    "hr.list_payrolls",
    "hr.update_payroll",
    "hr.approve_payroll",
    # crm
    "crm.list_opportunities",
    "crm.create_opportunity",
    "crm.update_opportunity_stage",
    "crm.qualify_leads",
    # banking
    "banking.list_transactions",
    "banking.check_balances",
    "banking.financial_summary",
    "banking.reconcile_transactions",
    # email
    "email.send_email",
    "email.check_inbox",
    "email.check_unread",
    # documents
    "documents.create_document",
    "documents.classify_document",
    "documents.list_tenant_documents",
    "documents.get_document_content",
    "documents.update_existing_document",
    "documents.search_documents",
    "documents.search_documents_semantic",
    "documents.answer_from_documents",
    # compliance
    "compliance.check_fiscal_deadlines",
    "compliance.fiscal_query",
    "compliance.check_boe_news",
    "compliance.check_quarter_preventive",
    # excel
    "excel.import_excel",
    "excel.read_excel",
    "excel.modify_excel",
    "excel.export_erp_data",
    "excel.list_available_datasets",
    # recruitment
    "recruitment.list_positions",
    "recruitment.create_position",
    "recruitment.list_candidates",
    "recruitment.process_cv",
    "recruitment.update_candidate_status",
    # rag / knowledge
    "rag.get_tenant_knowledge",
    "rag.upsert_tenant_knowledge",
    "rag.get_product_catalog",
    # memoria persistente del empleado (sólo activa si memory_enabled=True)
    "memory.remember",
    "memory.recall",
    "memory.recall_all",
]

VALID_EMPLOYEE_DOMAINS = {
    "billing",
    "documents",
    "compliance",
    "hr",
    "banking",
    "crm",
    "excel",
    "email",
    "marketing",
    "recruitment",
}

SPEC_PROMPT = """\
Eres el diseñador de agentes IA para AutomatizaCore, una plataforma de gestión empresarial española.
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
async def create_ai_employee_from_description(tenant_id: str, description: str) -> str:
    """
    Crea un nuevo empleado IA a partir de una descripción en lenguaje natural.
    Usa LLM para generar nombre, rol, dominio, system_prompt y skills apropiados.
    Args:
        tenant_id: ID del tenant
        description: Descripción en lenguaje natural del empleado deseado
    """
    llm = get_llm(temperature=0.7)
    prompt = SPEC_PROMPT.format(
        description=description,
        domains=", ".join(sorted(VALID_EMPLOYEE_DOMAINS)),
        skills=", ".join(AVAILABLE_SKILLS),
    )

    try:
        response = await llm.ainvoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        spec = json.loads(text.strip())
    except Exception as e:
        return f"Error generando especificación del empleado: {e}"

    name = spec.get("name", "Agente IA")
    role = spec.get("role", "Asistente")
    domain = spec.get("domain", "marketing")
    if domain not in VALID_EMPLOYEE_DOMAINS:
        domain = "marketing"
    system_prompt = spec.get("system_prompt", f"Soy {name}, {role}.")
    budget = float(spec.get("budget_limit_usd", 10.0))
    skills = [s for s in spec.get("skills", []) if s in AVAILABLE_SKILLS]

    try:
        async with AsyncSessionLocal() as db:
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
            await db.flush()

            for skill_module in skills:
                db.add(AgentSkill(employee_id=employee.id, tool_module=skill_module))

            await db.commit()

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
