"""
Agente de RRHH — calcula y genera nóminas (draft) para empleados.
Puede generar la nómina de un empleado individual (por NIF) o para TODOS
los empleados activos del tenant en un mes dado.

Usa el LLM configurado en llm_factory (Gemini/Anthropic/OpenAI/Groq).
Las nóminas se crean en modo DRAFT y requieren aprobación humana.
Tras aprobación, se genera el PDF y se guarda como TenantDocument.
"""
import logging
from calendar import monthrange
from datetime import UTC, datetime
from uuid import UUID

logger = logging.getLogger(__name__)

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from app.agents.agent_tools.documents import (
    create_document,
    get_document_content,
    list_tenant_documents,
    update_existing_document,
)
from app.agents.agent_tools.knowledge import get_tenant_knowledge, upsert_tenant_knowledge
from app.agents.base import AgentState
from app.agents.types import StepResult
from app.db.models.models import Employee, Payroll
from app.core.config import settings
from app.core.llm_factory import get_llm


def _get_llm():
    return get_llm(temperature=0)


# ─── Herramientas ─────────────────────────────────────────────────────────────

@tool
def calculate_and_create_payroll(tenant_id: str, nif: str, month: int, year: int, deductions: float = 0.0) -> str:
    """
    Calcula la nómina de UN empleado específico (por NIF), creándola en estado DRAFT.
    Args:
        tenant_id: ID del tenant
        nif: NIF del empleado
        month: Mes (1-12)
        year: Año (ej. 2025)
        deductions: Deducciones extra (ausencias, adelantos...)
    """
    import asyncio
    return asyncio.get_event_loop().run_until_complete(
        _create_payroll_async(tenant_id, nif, month, year, deductions)
    )


async def _create_payroll_async(tenant_id: str, nif: str, month: int, year: int, deductions: float) -> str:
    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Employee).where(
                    Employee.tenant_id == UUID(tenant_id),
                    Employee.nif == nif,
                )
            )
            employee = result.scalars().first()

            if not employee:
                return f"Error: Empleado con NIF {nif} no encontrado en RRHH."

            base_salary = float(employee.base_salary) if employee.base_salary else 0
            irpf_rate = float(employee.irpf_rate) if employee.irpf_rate is not None else 15.0

            # Desglose SS trabajador
            ss_cc = round(base_salary * 0.0470, 2)   # Contingencias comunes
            ss_des = round(base_salary * 0.0155, 2)   # Desempleo (indefinido)
            ss_fp = round(base_salary * 0.0010, 2)    # Formación profesional
            ss_mei = round(base_salary * 0.0013, 2)   # MEI
            irpf = round(base_salary * irpf_rate / 100, 2)
            total_ded = ss_cc + ss_des + ss_fp + ss_mei + irpf + deductions
            net_salary = max(0.0, base_salary - total_ded)

            last_day = monthrange(year, month)[1]
            start_date = datetime(year, month, 1, tzinfo=UTC)
            end_date   = datetime(year, month, last_day, tzinfo=UTC)

            payroll = Payroll(
                tenant_id=UUID(tenant_id),
                employee_id=employee.id,
                period_start=start_date,
                period_end=end_date,
                issue_date=datetime.now(UTC),
                base_salary=base_salary,
                ss_contingencias_comunes=ss_cc,
                ss_desempleo=ss_des,
                ss_formacion_profesional=ss_fp,
                ss_mei=ss_mei,
                irpf=irpf,
                other_deductions=deductions,
                deductions=total_ded,
                net_salary=net_salary,
                status="draft",
            )
            db.add(payroll)
            await db.commit()
            await db.refresh(payroll)

            # --- Generar PDF y Guardar en TenantDocument ---
            document_id = None
            try:
                from app.services.pdf_service import generate_payroll_pdf
                from app.db.models.models import TenantDocument, Tenant
                import os

                # Carga datos para el PDF
                async with AsyncSessionLocal() as db_pdf:
                    res_t = await db_pdf.execute(select(Tenant).where(Tenant.id == UUID(tenant_id)))
                    tenant_obj = res_t.scalar_one_or_none()
                    
                payroll_pdf_data = {
                    "employee": {
                        "name": employee.name,
                        "nif": employee.nif,
                        "position": employee.role or "Empleado",
                        "department": employee.department or "General",
                    },
                    "company": {
                        "name": tenant_obj.name if tenant_obj else "Empresa Cliente",
                        "nif": "B-00000000",
                        "address": "Calle Falsa 123, Madrid",
                    },
                    "period_start": start_date.isoformat(),
                    "period_end": end_date.isoformat(),
                    "issue_date": datetime.now(UTC).isoformat(),
                    "base_salary": base_salary,
                    "ss_contingencias_comunes": ss_cc,
                    "ss_desempleo": ss_des,
                    "ss_formacion_profesional": ss_fp,
                    "ss_mei": ss_mei,
                    "irpf": irpf,
                    "irpf_rate": irpf_rate,
                    "other_deductions": deductions,
                    "net_salary": net_salary,
                }

                pdf_bytes = generate_payroll_pdf(payroll_pdf_data)

                # Guardar en disco
                upload_dir = os.environ.get("UPLOAD_DIR", "/app/uploads")
                if not os.path.exists(upload_dir) and "WIN" in os.name.upper():
                    upload_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "uploads")
                os.makedirs(upload_dir, exist_ok=True)

                file_name = f"Nomina_{employee.name.replace(' ', '_')}_{month}_{year}.pdf"
                file_path = os.path.join(upload_dir, file_name)
                with open(file_path, "wb") as f:
                    f.write(pdf_bytes)

                # Registrar en BD
                new_doc = TenantDocument(
                    tenant_id=UUID(tenant_id),
                    file_name=file_name,
                    file_path=file_path,
                    file_type="application/pdf",
                    file_size=len(pdf_bytes),
                    category="nominas",
                    status="completed"
                )
                async with AsyncSessionLocal() as db_doc:
                    db_doc.add(new_doc)
                    await db_doc.commit()
                    await db_doc.refresh(new_doc)
                    document_id = str(new_doc.id)
            except Exception as pdf_err:
                logger.warning(f"Error PDF RRHH: {pdf_err}")

            # --- Emitir Evento para Automatización ---
            try:
                from app.services.event_bus import emit_event
                async with AsyncSessionLocal() as db_ev:
                    await emit_event(
                        db=db_ev,
                        tenant_id=UUID(tenant_id),
                        user_id=None,
                        event_name="payroll_created",
                        context={
                            "payroll_id": str(payroll.id),
                            "employee_name": employee.name,
                            "employee_nif": employee.nif,
                            "net_salary": float(net_salary),
                            "document_id": document_id
                        }
                    )
            except Exception as e:
                logger.warning("Error al emitir evento payroll_created para empleado %s: %s", nif, e)

        return (
            f"Pre-nómina generada: {employee.name} (NIF: {nif}) | "
            f"Bruto: {base_salary:.2f}€ | SS(CC {ss_cc:.2f}+Des {ss_des:.2f}+FP {ss_fp:.2f}+MEI {ss_mei:.2f}) | "
            f"IRPF({irpf_rate:.1f}%): {irpf:.2f}€ | "
            f"Neto: {net_salary:.2f}€ | Estado: DRAFT | ID: {payroll.id} | "
            f"Documento generado: {document_id or 'Fallo al generar PDF'}"
        )
    except Exception as e:
        return f"Error procesando nómina de {nif}: {str(e)}"


@tool
def generate_all_payrolls(tenant_id: str, month: int, year: int) -> str:
    """
    Genera las nóminas en borrador (DRAFT) para TODOS los empleados activos del tenant
    en un mes y año determinados. NO requiere NIF individual.
    Args:
        tenant_id: ID del tenant
        month: Mes (1-12)
        year: Año (ej. 2025)
    """
    import asyncio
    return asyncio.get_event_loop().run_until_complete(
        _generate_all_payrolls_async(tenant_id, month, year)
    )


async def _generate_all_payrolls_async(tenant_id: str, month: int, year: int) -> str:
    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Employee).where(Employee.tenant_id == UUID(tenant_id))
            )
            employees = result.scalars().all()

            if not employees:
                return "No se encontraron empleados activos en el tenant para generar nóminas."

            last_day = monthrange(year, month)[1]
            start_date = datetime(year, month, 1, tzinfo=UTC)
            end_date   = datetime(year, month, last_day, tzinfo=UTC)

            summary_lines = []
            for emp in employees:
                base_salary = float(emp.base_salary) if emp.base_salary else 0
                irpf_rate = float(emp.irpf_rate) if emp.irpf_rate is not None else 15.0

                ss_cc = round(base_salary * 0.0470, 2)
                ss_des = round(base_salary * 0.0155, 2)
                ss_fp = round(base_salary * 0.0010, 2)
                ss_mei_val = round(base_salary * 0.0013, 2)
                irpf = round(base_salary * irpf_rate / 100, 2)
                total_ded = ss_cc + ss_des + ss_fp + ss_mei_val + irpf
                net_salary = max(0.0, base_salary - total_ded)

                payroll = Payroll(
                    tenant_id=UUID(tenant_id),
                    employee_id=emp.id,
                    period_start=start_date,
                    period_end=end_date,
                    issue_date=datetime.now(UTC),
                    base_salary=base_salary,
                    ss_contingencias_comunes=ss_cc,
                    ss_desempleo=ss_des,
                    ss_formacion_profesional=ss_fp,
                    ss_mei=ss_mei_val,
                    irpf=irpf,
                    other_deductions=0,
                    deductions=total_ded,
                    net_salary=net_salary,
                    status="draft",
                )
                db.add(payroll)
                
                # --- Generar PDF silencioso para cada nómina del bloque ---
                try:
                    from app.services.pdf_service import generate_payroll_pdf
                    from app.db.models.models import TenantDocument, Tenant
                    import os
                    
                    payroll_pdf_data = {
                        "employee": {
                            "name": emp.name,
                            "nif": emp.nif,
                            "position": emp.role or "Empleado",
                            "department": emp.department or "General",
                        },
                        "company": {"name": "Empresa Cliente", "nif": "B-00000000", "address": "Sede Central"},
                        "period_start": start_date.isoformat(),
                        "period_end": end_date.isoformat(),
                        "issue_date": datetime.now(UTC).isoformat(),
                        "base_salary": base_salary,
                        "ss_contingencias_comunes": ss_cc,
                        "ss_desempleo": ss_des,
                        "ss_formacion_profesional": ss_fp,
                        "ss_mei": ss_mei_val,
                        "irpf": irpf,
                        "irpf_rate": irpf_rate,
                        "other_deductions": 0.0,
                        "net_salary": net_salary,
                    }
                    pdf_bytes = generate_payroll_pdf(payroll_pdf_data)
                    
                    file_name = f"Nomina_{emp.name.replace(' ', '_')}_{month}_{year}.pdf"
                    upload_dir = os.environ.get("UPLOAD_DIR", "/app/uploads")
                    if not os.path.exists(upload_dir) and "WIN" in os.name.upper():
                        upload_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "uploads")
                    os.makedirs(upload_dir, exist_ok=True)
                    file_path = os.path.join(upload_dir, file_name)
                    with open(file_path, "wb") as f: f.write(pdf_bytes)
                    
                    new_doc = TenantDocument(
                        tenant_id=UUID(tenant_id),
                        file_name=file_name,
                        file_path=file_path,
                        file_type="application/pdf",
                        file_size=len(pdf_bytes),
                        category="nominas",
                        status="completed"
                    )
                    db.add(new_doc)
                except Exception as e:
                    logger.warning("Error al generar o guardar PDF de nómina para empleado %s: %s", emp.name, e)

                summary_lines.append(
                    f"- {emp.name}: Bruto {base_salary:.2f}€ → Neto {net_salary:.2f}€"
                )

            await db.commit()

            # --- Emitir Evento Global para el bloque ---
            try:
                from app.services.event_bus import emit_event
                async with AsyncSessionLocal() as db_ev:
                    await emit_event(
                        db=db_ev,
                        tenant_id=UUID(tenant_id),
                        user_id=None,
                        event_name="payrolls_bulk_created",
                        context={
                            "count": len(employees),
                            "month": month,
                            "year": year
                        }
                    )
            except Exception as e:
                logger.warning("Error al emitir evento payrolls_bulk_created para tenant %s: %s", tenant_id, e)


        summary = "\n".join(summary_lines)
        return (
            f"Nóminas de {month}/{year} generadas en modo DRAFT para {len(employees)} empleados:\n"
            f"{summary}\n\n"
            f"IMPORTANTE: Las nóminas están en estado BORRADOR. "
            f"El responsable debe revisarlas y aprobarlas desde RRHH > Nóminas."
        )
    except Exception as e:
        return f"Error al generar nóminas en bloque: {str(e)}"


@tool
def list_employees(tenant_id: str) -> str:
    """
    Lista todos los empleados del tenant con su salario base y cargo.
    Útil antes de generar nóminas o para consultas de RRHH.
    Args:
        tenant_id: ID del tenant
    """
    import asyncio
    return asyncio.get_event_loop().run_until_complete(_list_employees_async(tenant_id))


async def _list_employees_async(tenant_id: str) -> str:
    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Employee).where(Employee.tenant_id == UUID(tenant_id))
            )
            employees = result.scalars().all()

        if not employees:
            return "No hay empleados registrados en el sistema."

        lines = [
            f"- {emp.name} | NIF: {emp.nif or 'N/A'} | "
            f"Cargo: {emp.role or 'N/A'} | Dpto: {emp.department or 'N/A'} | "
            f"Salario base: {float(emp.base_salary or 0):.2f}€"
            for emp in employees
        ]
        return f"Empleados ({len(employees)}):\n" + "\n".join(lines)
    except Exception as e:
        return f"Error listando empleados: {str(e)}"


tools = [
    calculate_and_create_payroll,
    generate_all_payrolls,
    list_employees,
    create_document,
    list_tenant_documents,
    update_existing_document,
    get_document_content,
    get_tenant_knowledge,
    upsert_tenant_knowledge,
]


# ─── Nodos del grafo ──────────────────────────────────────────────────────────

def hr_agent_node(state: AgentState):
    if "messages" not in state or not state["messages"]:
        sys_msg = SystemMessage(
            content=(
                "Eres el Agente de RRHH (Recursos Humanos) de la empresa automatizada. "
                "Tus capacidades:\n"
                "1. Generar nóminas individuales con `calculate_and_create_payroll` (requiere NIF, mes, año).\n"
                "2. Generar TODAS las nóminas del mes con `generate_all_payrolls` (solo mes y año).\n"
                "3. Consultar empleados con `list_employees`.\n"
                "4. Crear nuevos documentos (informes, extractos de datos en CSV, txt) con `create_document`.\n"
                "5. Listar documentos del tenant con `list_tenant_documents`.\n"
                "6. Leer el contenido de un documento con `get_document_content`.\n"
                "7. Modificar documentos con `update_existing_document`.\n"
                "8. Consultar la memoria a largo plazo con `get_tenant_knowledge`.\n"
                "9. Guardar hechos nuevos en la memoria con `upsert_tenant_knowledge`.\n"
                f"ID del Tenant actual: {state.get('tenant_id')}.\n"
                "Reglas:\n"
                "- Si se te pide exportar datos, listados de nóminas o empleados a CSV o texto, hazlo usando la herramienta `create_document`, especificando category='RRHH'.\n"
                "- Siempre genera nóminas en estado DRAFT. Las nóminas requieren aprobación humana.\n"
                "- Si el usuario no especifica mes/año, usa el mes y año actuales.\n"
                "- Para generar todas las nóminas, usa `generate_all_payrolls` directamente sin pedir NIF.\n"
                "- Si el usuario pide nómina de un empleado específico, primero usa `list_employees` para "
                "obtener el NIF si no lo conoces.\n"
                "- Siempre confirma qué nóminas se generaron y recuerda que deben aprobarse desde la UI."
            )
        )
        user_msg = HumanMessage(content=state["user_intent"])
        extra_init_messages = [sys_msg, user_msg]
        state["messages"] = extra_init_messages
    else:
        extra_init_messages = []

    llm_with_tools = _get_llm().bind_tools(tools)
    response = llm_with_tools.invoke(state["messages"])

    result_log = StepResult(
        step_id=f"hr_step_{datetime.now().timestamp()}",
        description="Procesando solicitud de RRHH...",
        status="completed",
        action_taken=(
            "Invocando herramientas de RRHH"
            if response.tool_calls
            else "Asistencia RRHH completada."
        ),
    )

    if "agent_results" not in state:
        state["agent_results"] = []

    state["agent_results"].append(result_log.model_dump())
    return {"messages": extra_init_messages + [response], "agent_results": state["agent_results"]}


def hr_finalize_node(state: AgentState):
    """Cierra el flujo del agente de RRHH."""
    last_msg = state["messages"][-1]

    final_result = StepResult(
        step_id="hr_final",
        description="Agente RRHH ha finalizado.",
        status="completed",
        action_taken=(
            last_msg.content
            if isinstance(last_msg.content, str)
            else "Borradores generados localmente."
        ),
    )

    return {"status": "done", "agent_results": [final_result.model_dump()]}


# ─── Compilar grafo ───────────────────────────────────────────────────────────

workflow = StateGraph(AgentState)
workflow.add_node("hr_agent", hr_agent_node)
workflow.add_node("tools", ToolNode(tools))
workflow.add_node("finalize", hr_finalize_node)

workflow.set_entry_point("hr_agent")
workflow.add_conditional_edges("hr_agent", tools_condition)
workflow.add_edge("tools", "hr_agent")

graph = workflow.compile()
