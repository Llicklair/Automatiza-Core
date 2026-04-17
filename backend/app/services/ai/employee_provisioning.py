"""employee_provisioning — Seeding and LLM-driven background provisioning for AIEmployee."""

from __future__ import annotations

import json
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.ai_employees import AgentSkill, AIEmployee
from app.db.models.tasks import Task
from app.services.ai.employee_crud import _KNOWN_SKILLS, _SKILL_LABELS

logger = logging.getLogger(__name__)

# ── Built-in employee definitions ───────────────────────────────────────────

_BUILTIN_EMPLOYEES_DATA = [
    {
        "name": "Ana Valdés",
        "role": "Directora Financiera",
        "domain": "billing",
        "system_prompt": (
            "Eres Ana Valdés, Directora Financiera de la empresa. "
            "Tu responsabilidad es gestionar facturas, cobros, albaranes y la salud financiera del negocio. "
            "Actúas de forma proactiva: detectas facturas vencidas, envías recordatorios y mantienes el flujo de caja. "
            "Comunicas siempre en español, con tono profesional y directo."
        ),
    },
    {
        "name": "Carlos Herrero",
        "role": "Responsable de RRHH",
        "domain": "hr",
        "system_prompt": (
            "Eres Carlos Herrero, Responsable de Recursos Humanos. "
            "Gestionas empleados, nóminas, contratos y el bienestar del equipo. "
            "Procesas nóminas con precisión, alertas de vacaciones y revisas cumplimiento laboral. "
            "Comunicas siempre en español, con tono cercano y profesional."
        ),
    },
    {
        "name": "Sofía Martín",
        "role": "Asistente de Comunicación",
        "domain": "email",
        "system_prompt": (
            "Eres Sofía Martín, Asistente de Comunicación. "
            "Gestionas el correo electrónico de la empresa: revisas el buzón, redactas respuestas "
            "y envías comunicaciones a clientes y proveedores. "
            "Siempre revisas antes de enviar y mantienes un tono profesional en español."
        ),
    },
    {
        "name": "Javier Romero",
        "role": "Responsable Comercial",
        "domain": "crm",
        "system_prompt": (
            "Eres Javier Romero, Responsable Comercial de la empresa. "
            "Gestionas el CRM: registras oportunidades, haces seguimiento de clientes, "
            "creas actividades comerciales y mantienes el pipeline actualizado. "
            "Eres proactivo en detectar oportunidades de venta y en mantener relaciones con clientes. "
            "Comunicas siempre en español, con tono comercial y profesional."
        ),
    },
    {
        "name": "Miguel Torres",
        "role": "Responsable de Banca",
        "domain": "banking",
        "system_prompt": (
            "Eres Miguel Torres, Responsable de Banca de la empresa. "
            "Controlas los movimientos bancarios, reconcilias extractos, supervisas transferencias "
            "y mantienes el control de tesorería. "
            "Alertas sobre descubiertos, pagos pendientes y anomalías en cuenta. "
            "Comunicas siempre en español, con tono riguroso y profesional."
        ),
    },
    {
        "name": "Laura Jiménez",
        "role": "Asesora Fiscal y Compliance",
        "domain": "compliance",
        "system_prompt": (
            "Eres Laura Jiménez, Asesora Fiscal y de Compliance de la empresa. "
            "Gestionas las obligaciones tributarias: modelos 303, 130, retenciones, plazos del BOE "
            "y alertas de vencimientos fiscales. "
            "Asesoras sobre normativa aplicable y mantienes al día el calendario fiscal. "
            "Comunicas siempre en español, con tono técnico, preciso y profesional."
        ),
    },
    {
        "name": "Elena Ruiz",
        "role": "Gestora de Documentación",
        "domain": "documents",
        "system_prompt": (
            "Eres Elena Ruiz, Gestora de Documentación de la empresa. "
            "Procesas, clasificas y analizas documentos: contratos, facturas recibidas, albaranes y archivos. "
            "Extraes información clave mediante OCR, buscas en el repositorio documental "
            "y garantizas que la documentación esté ordenada y accesible. "
            "Comunicas siempre en español, con tono metódico y profesional."
        ),
    },
    {
        "name": "David Sánchez",
        "role": "Analista de Datos",
        "domain": "excel",
        "system_prompt": (
            "Eres David Sánchez, Analista de Datos de la empresa. "
            "Creas y gestionas hojas de cálculo, cruzas tablas de datos, generas informes en Excel "
            "y elaboras resúmenes ejecutivos a partir de los datos del negocio. "
            "Trabajas con precisión y entregas resultados listos para tomar decisiones. "
            "Comunicas siempre en español, con tono analítico y profesional."
        ),
    },
]


# ── Seed ────────────────────────────────────────────────────────────────────


async def seed_builtin(tenant_id, db: AsyncSession) -> list[str]:
    """Crea empleados built-in. Retorna lista de nombres creados."""
    created = []
    for emp_data in _BUILTIN_EMPLOYEES_DATA:
        existing = await db.execute(
            select(AIEmployee).where(
                AIEmployee.tenant_id == tenant_id,
                AIEmployee.domain == emp_data["domain"],
                AIEmployee.is_builtin == True,  # noqa: E712
            )
        )
        if existing.scalar_one_or_none():
            continue
        employee = AIEmployee(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            is_builtin=True,
            status="idle",
            **emp_data,
        )
        db.add(employee)
        created.append(emp_data["name"])
    await db.commit()
    return created


# ── Background provisioning ────────────────────────────────────────────────


async def provision_employee_bg(
    employee_id: str, tenant_id: str, name: str, role_description: str,
) -> None:
    """Llama al LLM para configurar el agente (ejecutar en background task)."""
    from langchain_core.messages import HumanMessage

    from app.core.llm_factory import get_llm
    from app.db.base import AsyncSessionLocal

    all_skill_labels = ", ".join(f"{k} ({v})" for k, v in _SKILL_LABELS.items())

    prompt = (
        f"Eres un asistente de configuración de agentes IA empresariales.\n"
        f"Se ha creado un nuevo agente: nombre='{name}', rol solicitado='{role_description}'.\n"
        f"Skills disponibles: {all_skill_labels}.\n\n"
        f"Devuelve SOLO un JSON válido con esta estructura (sin texto extra):\n"
        f"{{\n"
        f'  "domain": "<billing|hr|email|crm|banking|compliance|excel|documents|custom>",\n'
        f'  "role": "<título profesional conciso en español>",\n'
        f'  "system_prompt": "<prompt detallado en español, primera persona, 3-5 frases profesionales>",\n'
        f'  "skills": ["<tool_module>", ...],\n'
        f'  "can_do": ["<capacidad concreta 1>", "<capacidad 2>", ...],\n'
        f'  "cannot_do": ["<limitación concreta 1>", ...],\n'
        f'  "vs_others": "<1-2 frases comparando este agente con otros del equipo: en qué se diferencia y cuándo usarlo>"\n'
        f"}}\n"
        f"Asigna solo las skills realmente relevantes para el rol. can_do debe reflejar las skills asignadas. "
        f"cannot_do son acciones fuera de su dominio. vs_others compara con agentes típicos del equipo (facturación, RRHH, CRM, etc.)."
    )

    try:
        llm = get_llm(temperature=0)
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1].lstrip("json").strip()
        data = json.loads(raw)

        assigned_skills = [s for s in data.get("skills", []) if s in _KNOWN_SKILLS]
        unassigned_skills = [s for s in _KNOWN_SKILLS if s not in assigned_skills]

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(AIEmployee).where(AIEmployee.id == employee_id))
            emp = result.scalar_one_or_none()
            if not emp:
                return

            emp.domain = data.get("domain", "custom")
            emp.role = data.get("role", role_description)
            emp.system_prompt = data.get("system_prompt", emp.system_prompt)
            emp.status = "idle"

            for tool_module in assigned_skills:
                session.add(AgentSkill(employee_id=emp.id, tool_module=tool_module))

            can_do = data.get("can_do", [_SKILL_LABELS[s] for s in assigned_skills])
            cannot_do = data.get("cannot_do", [_SKILL_LABELS[s] for s in unassigned_skills[:3]])
            vs_others = data.get("vs_others", "")

            summary_lines = [
                f"✅ Agente **{emp.name}** configurado como *{emp.role}* (dominio: {emp.domain}).",
                "",
                "**Puede hacer:**",
                *[f"  • {item}" for item in can_do],
                "",
                "**No puede hacer:**",
                *[f"  • {item}" for item in cannot_do],
            ]
            if vs_others:
                summary_lines += ["", "**Respecto a otros agentes:**", f"  {vs_others}"]

            summary = "\n".join(summary_lines)

            provision_task = Task(
                id=uuid.uuid4(),
                tenant_id=emp.tenant_id,
                created_by=None,
                domain="coordinator",
                user_intent=f"Configuración automática de {emp.name} ({role_description})",
                status="done",
                agent_results=[
                    {
                        "agent": "coordinator",
                        "success": True,
                        "summary": summary,
                        "output": {
                            "action": "chat_response",
                            "response": summary,
                        },
                    }
                ],
            )
            session.add(provision_task)
            await session.commit()
            logger.info(
                "Agente '%s' provisionado (domain=%s, skills=%d)",
                name, emp.domain, len(assigned_skills),
            )

    except Exception as exc:
        logger.error("Error provisionando agente '%s': %s", name, exc)
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(AIEmployee).where(AIEmployee.id == employee_id)
                )
                emp = result.scalar_one_or_none()
                if emp and emp.status == "pending_setup":
                    emp.status = "idle"
                    await session.commit()
        except Exception as e:
            logger.debug("Error reverting pending_setup status for agent '%s': %s", name, e)
