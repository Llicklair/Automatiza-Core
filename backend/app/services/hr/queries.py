"""HR queries — read-only operations (CQRS-lite).

No side effects: no INSERT/UPDATE/DELETE, no file writes, no commits.
"""

import base64
import logging
import os
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.hr import Attendance, Candidate, Expense, LeaveRequest, RecruitmentPosition, WorkSchedule
from app.db.models.hr_documents import HRDocument
from app.db.models.models import Employee
from app.prompts import load_prompt

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads"))

# Tasas SS empleado 2024/2025 — Regimen General (trabajador)
_SS_CONTINGENCIAS = 0.0470
_SS_DESEMPLEO = 0.0155
_SS_FP = 0.0010
_SS_MEI = 0.0010

VALID_CANDIDATE_STATUSES = {"new", "reviewed", "shortlisted", "rejected", "hired"}


# ── Calculo de nomina ────────────────────────────────────────────────────────


def calc_payroll(base_salary: float, irpf_rate: float) -> dict:
    """Calcula deducciones de SS e IRPF sobre el salario base mensual."""
    ss_cc = round(base_salary * _SS_CONTINGENCIAS, 2)
    ss_des = round(base_salary * _SS_DESEMPLEO, 2)
    ss_fp = round(base_salary * _SS_FP, 2)
    ss_mei = round(base_salary * _SS_MEI, 2)
    total_ss = round(ss_cc + ss_des + ss_fp + ss_mei, 2)
    irpf = round(base_salary * (irpf_rate / 100), 2)
    deductions = round(total_ss + irpf, 2)
    net = round(base_salary - deductions, 2)
    return {
        "ss_contingencias_comunes": ss_cc,
        "ss_desempleo": ss_des,
        "ss_formacion_profesional": ss_fp,
        "ss_mei": ss_mei,
        "total_ss": total_ss,
        "irpf": irpf,
        "deductions": deductions,
        "net_salary": net,
    }


# ── Employee queries ─────────────────────────────────────────────────────────


async def list_employees(tenant_id, db: AsyncSession) -> list[Employee]:
    result = await db.execute(
        select(Employee).where(Employee.tenant_id == tenant_id).order_by(desc(Employee.created_at))
    )
    return list(result.scalars().all())


async def get_employee(employee_id: UUID, tenant_id, db: AsyncSession) -> Employee | None:
    result = await db.execute(
        select(Employee).where(Employee.id == employee_id, Employee.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


# ── Document helpers (private) ───────────────────────────────────────────────


def _load_sepe_logo_b64() -> str:
    """Load SEPE logo as a data URI PNG for embedding in HTML."""
    candidates = [
        os.path.join(os.path.dirname(__file__), "assets", "sepe_logo.png"),
        os.path.join(
            os.path.dirname(__file__), "..", "api", "v1", "routes", "assets", "sepe_logo.png"
        ),
    ]
    for path in candidates:
        p = os.path.normpath(path)
        if os.path.isfile(p):
            with open(p, "rb") as f:
                return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    return ""


_SEPE_LOGO_URI = _load_sepe_logo_b64()

_HEADER_SEPE = f"""
<table style="width:100%;border:none;margin-bottom:6px">
  <tr>
    <td style="border:none;padding:0;vertical-align:top;width:60%">
      <div style="font-family:Arial,sans-serif;font-size:7.5pt;color:#555;line-height:1.5">
        <strong style="font-size:8pt;color:#222">GOBIERNO DE ESPANA</strong><br>
        MINISTERIO DE TRABAJO Y ECONOMIA SOCIAL<br>
        SERVICIO PUBLICO DE EMPLEO ESTATAL
      </div>
    </td>
    <td style="border:none;padding:0;text-align:right;vertical-align:top">
      {'<img src="' + _SEPE_LOGO_URI + '" style="height:38px" alt="SEPE"/>' if _SEPE_LOGO_URI else '<span style="font-size:16pt;font-weight:bold;color:#005495">SEPE</span>'}
    </td>
  </tr>
</table>
<hr style="border:none;border-top:2px solid #005495;margin:4px 0 14px">
"""

_HEADER_EMPRESA = """
<div style="font-family:Arial,sans-serif;font-size:9pt;color:#333;margin-bottom:16px">
  <strong style="font-size:12pt;color:#1a1a1a">[EMPRESA_NOMBRE]</strong><br>
  NIF: [NIF_EMPRESA] &nbsp;|&nbsp; [DIRECCION_EMPRESA]<br>
  <span style="font-size:8pt;color:#666">Tel.: [TEL_EMPRESA] &nbsp;·&nbsp; [EMAIL_EMPRESA]</span>
</div>
<hr style="border:none;border-top:1px solid #ccc;margin:4px 0 14px">
"""

DOC_TYPE_LABELS = {
    "contract": "Contrato de Trabajo",
    "nda": "Acuerdo de Confidencialidad (NDA)",
    "termination": "Carta de Despido",
    "settlement": "Finiquito",
    "addendum": "Adenda Contractual",
    "other": "Documento Laboral",
}

# ── Header instructions per doc type ─────────────────────────────────────────

_HEADER_INSTRUCTIONS: dict[str, str] = {
    "contract": f"""
CABECERA OBLIGATORIA para contratos de trabajo — copia este HTML exactamente al inicio del documento:
{_HEADER_SEPE}

ESTRUCTURA DEL CONTRATO (sigue este orden):
1. Cabecera SEPE (arriba)
2. Titulo: "CONTRATO DE TRABAJO" (h1)
3. Subtitulo con modalidad (ej: "INDEFINIDO ORDINARIO — Codigo 100")
4. Tabla: DATOS DE LA EMPRESA (razon social, CIF, CNAE, CCC, domicilio, representante)
5. Tabla: DATOS DEL TRABAJADOR (nombre, DNI/NIE, NAF, fecha nacimiento, domicilio, grupo cotizacion)
6. Seccion: DURACION DE LA RELACION LABORAL (fecha inicio, fin si temporal, periodo de prueba)
7. Seccion: JORNADA DE TRABAJO (completa/parcial, horas/semana, horario, distribucion)
8. Seccion: RETRIBUCION (salario base, complementos, pagas extra, total anual bruto)
9. Seccion: CONVENIO COLECTIVO APLICABLE
10. Seccion: CLAUSULAS ADICIONALES
11. Bloque de firmas (empresa + trabajador + fecha y lugar)
12. Nota discreta al final
""",
    "settlement": """
ESTRUCTURA DEL FINIQUITO (sigue este orden):
1. Cabecera empresa (nombre, NIF, direccion)
2. Titulo: "FINIQUITO / DOCUMENTO DE LIQUIDACION Y SALDO" (h1)
3. Datos empresa y trabajador en tabla
4. Parrafo de declaracion de extincion (causa, fecha)
5. Tabla DESGLOSE DE LA LIQUIDACION con columnas CONCEPTOS | DIAS/BASE | DEVENGOS | DEDUCCIONES:
   - Parte proporcional de vacaciones no disfrutadas
   - Parte proporcional paga extra (si aplica)
   - Parte proporcional aguinaldo (si aplica)
   - MEI (si aplica)
   - Indemnizacion (si aplica — indicar dias/ano y base)
   - IRPF (%)
   - Cotizacion SS obrero
6. TOTAL PERCEPCIONES | TOTAL DEDUCCIONES | IMPORTE LIQUIDO A PERCIBIR
7. Parrafo legal de saldo y finiquito (el trabajador declara no tener mas reclamaciones)
8. Espacio para 3 firmas: empresa, trabajador, representante sindical (si aplica)
9. Lugar, fecha y nota discreta
""",
    "termination": """
ESTRUCTURA CARTA DE DESPIDO:
1. Cabecera empresa
2. Lugar y fecha
3. Datos destinatario (trabajador)
4. Cuerpo: causa de despido con fundamento legal (ET art. 52/54 segun sea objetivo/disciplinario)
5. Efectos: fecha de efectividad, indemnizacion si procede
6. Firma empresa
""",
}

_DEFAULT_HEADER_INSTRUCTION = """
Usa un encabezado profesional con datos de empresa, titulo del documento y datos de las partes.
"""


def _get_system_prompt(doc_type: str) -> str:
    """Build system prompt for the given document type."""
    base = load_prompt("hr_documents")
    header = _HEADER_INSTRUCTIONS.get(doc_type, _DEFAULT_HEADER_INSTRUCTION)
    return base + header


async def _build_employee_context(employee_id: str, tenant_id, db: AsyncSession) -> str:
    """Fetch employee data and format as LLM context string."""
    try:
        from app.db.models.hr import Employee as HREmployee

        result = await db.execute(
            select(HREmployee).where(
                HREmployee.id == employee_id,
                HREmployee.tenant_id == tenant_id,
            )
        )
        emp = result.scalar_one_or_none()
        if not emp:
            return ""
        return (
            f"\nDATOS DEL TRABAJADOR (usa estos exactamente):\n"
            f"- Nombre completo: {emp.name}\n"
            f"- DNI/NIE: {emp.nif or '[DNI_EMPLEADO]'}\n"
            f"- NAF (Num. Afiliacion SS): {getattr(emp, 'numero_afiliacion_ss', None) or '[NAF]'}\n"
            f"- Categoria profesional: {getattr(emp, 'categoria_profesional', None) or emp.role or '[CATEGORIA]'}\n"
            f"- Grupo de cotizacion: {getattr(emp, 'grupo_cotizacion', None) or '[GRUPO_COT]'}\n"
            f"- Departamento: {emp.department or '[DEPARTAMENTO]'}\n"
            f"- Tipo de contrato: {getattr(emp, 'tipo_contrato', None) or '[TIPO_CONTRATO]'}\n"
            f"- Jornada: {getattr(emp, 'jornada_tipo', 'completa')} — {getattr(emp, 'jornada_horas_semana', None) or 40}h/semana\n"
            f"- Convenio colectivo: {getattr(emp, 'convenio_colectivo', None) or '[CONVENIO]'}\n"
            f"- Salario base mensual: {emp.base_salary or '[SALARIO]'}€\n"
            f"- IRPF: {emp.irpf_rate or 15}%\n"
            f"- Fecha incorporacion: {emp.join_date or '[FECHA_INICIO]'}\n"
            f"- Periodo de prueba: {getattr(emp, 'periodo_prueba_dias', None) or '[PERIODO_PRUEBA]'} dias\n"
        )
    except Exception as e:
        logger.warning("No se pudo cargar empleado %s: %s", employee_id, e)
        return ""


async def _build_company_context(tenant_id, db: AsyncSession) -> str:
    """Fetch tenant data and format as LLM context string."""
    try:
        from app.db.models.auth import Tenant

        result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            return ""
        return (
            f"\nDATOS REALES DE LA EMPRESA (usa estos exactamente, no los sustituyas por placeholders):\n"
            f"- Razon social: {tenant.name}\n"
            f"- CIF/NIF: {tenant.nif or '[CIF_EMPRESA]'}\n"
            f"- Direccion: {tenant.address or '[DIRECCION_EMPRESA]'}\n"
            f"- Telefono: {tenant.phone or '[TEL_EMPRESA]'}\n"
            f"- Email de contacto: {tenant.contact_email or '[EMAIL_EMPRESA]'}\n"
        )
    except Exception as e:
        logger.warning("No se pudo cargar datos del tenant: %s", e)
        return ""


def _strip_markdown_wrapper(content: str) -> str:
    """Remove ```html ... ``` wrappers from LLM output."""
    if content.startswith("```"):
        lines = content.split("\n")
        start = 1 if lines[0].startswith("```") else 0
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        return "\n".join(lines[start:end]).strip()
    return content


# ── Document queries ─────────────────────────────────────────────────────────


async def list_documents(
    tenant_id,
    db: AsyncSession,
    *,
    doc_type: str | None = None,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """List HR documents for a tenant with optional filters."""
    query = (
        select(HRDocument)
        .where(HRDocument.tenant_id == tenant_id)
        .order_by(desc(HRDocument.created_at))
        .limit(limit)
        .offset(offset)
    )
    if doc_type:
        query = query.where(HRDocument.doc_type == doc_type)
    if status_filter:
        query = query.where(HRDocument.status == status_filter)

    result = await db.execute(query)
    docs = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "doc_type": d.doc_type,
            "title": d.title,
            "employee_name": d.employee_name,
            "content_html": d.content_html,
            "status": d.status,
            "instructions": d.instructions,
            "created_at": d.created_at.isoformat(),
            "approved_at": d.approved_at.isoformat() if d.approved_at else None,
        }
        for d in docs
    ]


async def get_document(doc_id: str, tenant_id, db: AsyncSession) -> dict:
    """Fetch a single HR document. Raises ValueError if not found."""
    result = await db.execute(
        select(HRDocument).where(
            HRDocument.id == doc_id,
            HRDocument.tenant_id == tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise ValueError("Documento no encontrado")
    return {
        "id": str(doc.id),
        "doc_type": doc.doc_type,
        "title": doc.title,
        "employee_name": doc.employee_name,
        "content_html": doc.content_html,
        "status": doc.status,
        "instructions": doc.instructions,
        "created_at": doc.created_at.isoformat(),
        "approved_at": doc.approved_at.isoformat() if doc.approved_at else None,
    }


# ── Recruitment queries ──────────────────────────────────────────────────────


async def list_positions(
    db: AsyncSession, tenant_id: UUID, status_filter: str = "all"
) -> list[dict]:
    q = select(RecruitmentPosition).where(RecruitmentPosition.tenant_id == tenant_id)
    if status_filter != "all":
        q = q.where(RecruitmentPosition.status == status_filter)

    result = await db.execute(q.order_by(RecruitmentPosition.created_at.desc()))
    positions = result.scalars().all()

    count_q = (
        select(Candidate.position_id, func.count(Candidate.id))
        .where(Candidate.tenant_id == tenant_id)
        .group_by(Candidate.position_id)
    )
    count_result = await db.execute(count_q)
    counts = dict(count_result.all())

    out = []
    for p in positions:
        out.append(
            {
                "id": p.id,
                "title": p.title,
                "department": p.department,
                "description": p.description,
                "required_skills": p.required_skills,
                "experience_min_years": float(p.experience_min_years)
                if p.experience_min_years
                else 0,
                "salary_range_min": float(p.salary_range_min) if p.salary_range_min else None,
                "salary_range_max": float(p.salary_range_max) if p.salary_range_max else None,
                "status": p.status,
                "candidate_count": counts.get(p.id, 0),
            }
        )
    return out


async def list_candidates(db: AsyncSession, tenant_id: UUID, position_id: UUID) -> list:
    result = await db.execute(
        select(Candidate)
        .where(
            Candidate.tenant_id == tenant_id,
            Candidate.position_id == position_id,
        )
        .order_by(Candidate.score.desc().nullslast())
    )
    return list(result.scalars().all())


# ── Schedule queries ─────────────────────────────────────────────────────────


async def list_schedules(db: AsyncSession, tenant_id) -> dict:
    """Return schedules grouped by employee_id → list of day rows."""
    result = await db.execute(
        select(WorkSchedule)
        .where(WorkSchedule.tenant_id == tenant_id)
        .order_by(WorkSchedule.employee_id, WorkSchedule.day_of_week)
    )
    rows = result.scalars().all()
    grouped: dict = {}
    for r in rows:
        key = str(r.employee_id)
        grouped.setdefault(key, []).append(_schedule_row(r))
    return grouped


async def get_employee_schedule(db: AsyncSession, tenant_id, employee_id: UUID) -> list[dict]:
    result = await db.execute(
        select(WorkSchedule)
        .where(WorkSchedule.tenant_id == tenant_id, WorkSchedule.employee_id == employee_id)
        .order_by(WorkSchedule.day_of_week)
    )
    return [_schedule_row(r) for r in result.scalars().all()]


def _schedule_row(r: WorkSchedule) -> dict:
    return {
        "id": str(r.id),
        "employee_id": str(r.employee_id),
        "day_of_week": r.day_of_week,
        "start_time": r.start_time,
        "end_time": r.end_time,
        "active": r.active,
    }


# ── Attendance queries ────────────────────────────────────────────────────────


async def list_attendance(db: AsyncSession, tenant_id, date=None) -> list[dict]:
    """Return attendance records for a day (defaults to today)."""
    from datetime import date as date_type

    target = date or date_type.today()
    result = await db.execute(
        select(Attendance)
        .where(Attendance.tenant_id == tenant_id, Attendance.date == target)
        .order_by(Attendance.clock_in)
    )
    return [_attendance_row(r) for r in result.scalars().all()]


async def get_currently_working(db: AsyncSession, tenant_id) -> list[dict]:
    """Return attendance records where clock_out IS NULL."""
    result = await db.execute(
        select(Attendance)
        .where(Attendance.tenant_id == tenant_id, Attendance.clock_out.is_(None))
        .order_by(Attendance.clock_in)
    )
    return [_attendance_row(r) for r in result.scalars().all()]


def _attendance_row(r: Attendance) -> dict:
    return {
        "id": str(r.id),
        "employee_id": str(r.employee_id),
        "clock_in": r.clock_in.isoformat() if r.clock_in else None,
        "clock_out": r.clock_out.isoformat() if r.clock_out else None,
        "date": r.date.isoformat() if r.date else None,
        "notes": r.notes,
    }


# ── Leave request queries ─────────────────────────────────────────────────────


async def list_leave_requests(
    db: AsyncSession, tenant_id, status_filter: str | None = None
) -> list[dict]:
    q = select(LeaveRequest).where(LeaveRequest.tenant_id == tenant_id)
    if status_filter:
        q = q.where(LeaveRequest.status == status_filter)
    result = await db.execute(q.order_by(LeaveRequest.created_at.desc()))
    return [_leave_request_row(r) for r in result.scalars().all()]


def _leave_request_row(r: LeaveRequest) -> dict:
    return {
        "id": str(r.id),
        "employee_id": str(r.employee_id),
        "leave_type": r.leave_type,
        "start_date": r.start_date.isoformat() if r.start_date else None,
        "end_date": r.end_date.isoformat() if r.end_date else None,
        "status": r.status,
        "notes": r.notes,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


# ── Expense queries ───────────────────────────────────────────────────────────


async def list_expenses(
    db: AsyncSession, tenant_id, status_filter: str | None = None, employee_id=None
) -> list[dict]:
    q = (
        select(Expense)
        .where(Expense.tenant_id == tenant_id)
        .options(__import__("sqlalchemy.orm", fromlist=["selectinload"]).selectinload(Expense.employee))
    )
    if status_filter:
        q = q.where(Expense.status == status_filter)
    if employee_id:
        q = q.where(Expense.employee_id == employee_id)
    result = await db.execute(q.order_by(Expense.created_at.desc()))
    return [_expense_row(r) for r in result.scalars().all()]


def _expense_row(r: Expense) -> dict:
    emp = r.employee if r.employee else None
    return {
        "id": str(r.id),
        "employee_id": str(r.employee_id),
        "employee_name": emp.name if emp else None,
        "amount": float(r.amount),
        "category": r.category,
        "description": r.description,
        "date": r.date.isoformat() if r.date else None,
        "status": r.status,
        "receipt_filename": r.receipt_filename,
        "notes": r.notes,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


async def get_expense_receipt_path(db: AsyncSession, tenant_id, expense_id) -> tuple[str, str] | None:
    result = await db.execute(
        select(Expense).where(Expense.id == expense_id, Expense.tenant_id == tenant_id)
    )
    exp = result.scalar_one_or_none()
    if not exp or not exp.receipt_path:
        return None
    return exp.receipt_path, exp.receipt_filename or "recibo"


# ── Re-exports from sub-modules ──────────────────────────────────────────────

from app.services.hr._employee_docs import (  # noqa: E402, F401
    get_employee_document,
    list_employee_documents,
    read_document_file,
)
from app.services.hr._payroll import (  # noqa: E402, F401
    build_payroll_pdf,
    download_payroll_pdf,
    list_payrolls,
    preview_payroll,
)
from app.services.hr._special_docs import load_employee_and_tenant  # noqa: E402, F401
