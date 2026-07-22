"""HR queries — read-only operations (CQRS-lite).

No side effects: no INSERT/UPDATE/DELETE, no file writes, no commits.
"""

import base64
import logging
import os
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetime_utils import local_today
from app.db.models.hr import (
    Attendance,
    Candidate,
    Expense,
    LeaveRequest,
    RecruitmentPosition,
    WorkSchedule,
)
from app.db.models.hr_documents import HRDocument
from app.db.models.models import Employee
from app.prompts import load_prompt

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads"))

# Tasas SS empleado — Régimen General (trabajador)
_SS_CONTINGENCIAS = 0.0470
_SS_DESEMPLEO = 0.0155  # contrato indefinido; temporal = 0,0160
_SS_FP = 0.0010

# MEI (Mecanismo de Equidad Intergeneracional) — parte del TRABAJADOR. Sube
# 0,01 pp/año hasta 2029 (RD-ley 2/2023). Tipos del trabajador por año (BOE):
#   2023: 0,10 % · 2024: 0,12 % · 2025: 0,13 % · 2026: 0,15 %
# Revisar cada año. Antes el código usaba un 0,10 % fijo (tipo de 2023),
# infra-deduciendo el MEI en 2024+.
_MEI_TRABAJADOR = {
    2023: 0.0010,
    2024: 0.0012,
    2025: 0.0013,
    2026: 0.0015,
}
_MEI_DEFAULT_YEAR = max(_MEI_TRABAJADOR)


def mei_trabajador(year: int | None = None) -> float:
    """Tipo del MEI a cargo del trabajador para el año dado (default: más reciente)."""
    if year in _MEI_TRABAJADOR:
        return _MEI_TRABAJADOR[year]
    return _MEI_TRABAJADOR[_MEI_DEFAULT_YEAR]


# Tope máximo de la base de cotización MENSUAL (Régimen General). La SS se
# cotiza sobre min(salario, tope): por encima del tope NO se cotiza (salvo la
# cuota de solidaridad sobre el exceso, no incluida en este MVP). El IRPF, en
# cambio, se retiene sobre el salario íntegro sin tope.
# Fuente: Órdenes anuales de cotización (BOE). Revisar cada año.
_BASE_MAX_COTIZACION_MENSUAL = {
    2024: 4720.50,
    2025: 4909.50,
    2026: 5101.20,
}
_BASE_MAX_DEFAULT_YEAR = max(_BASE_MAX_COTIZACION_MENSUAL)


def base_maxima_cotizacion(year: int | None = None) -> float:
    """Tope mensual de cotización del año dado. Si el año no está en la tabla,
    usa el más reciente conocido (las órdenes posteriores solo suben el tope)."""
    if year in _BASE_MAX_COTIZACION_MENSUAL:
        return _BASE_MAX_COTIZACION_MENSUAL[year]
    return _BASE_MAX_COTIZACION_MENSUAL[_BASE_MAX_DEFAULT_YEAR]


# Cuota de solidaridad (RD-ley 2/2023, vigente desde 2025): cotización adicional
# sobre la parte del salario que EXCEDE la base máxima, en tres tramos. Se
# reparte entre empresa y trabajador en la MISMA proporción que las
# contingencias comunes (trabajador 4,70 de 28,30 = 16,61 %). Aquí se calcula la
# parte del TRABAJADOR, que es la que reduce el neto. Tipos TOTALES por año (BOE);
# antes de 2025 no existía. Revisar cada año (suben progresivamente hasta 2045).
_CC_TOTAL = 0.2830  # contingencias comunes: 23,60 empresa + 4,70 trabajador
_SOLIDARIDAD_FRACCION_TRABAJADOR = _SS_CONTINGENCIAS / _CC_TOTAL  # ≈ 0,1661
# Tramos como múltiplos de la base máxima: [1,0–1,1), [1,1–1,5), [1,5–∞).
_SOLIDARIDAD_TRAMOS = ((1.0, 1.10), (1.10, 1.50), (1.50, None))
# Tipos totales (empresa + trabajador) por tramo y año.
_CUOTA_SOLIDARIDAD_TIPOS = {
    2025: (0.0092, 0.0100, 0.0117),
    2026: (0.0115, 0.0125, 0.0146),
}


def cuota_solidaridad_trabajador(base_salary: float, year: int | None = None) -> float:
    """Parte de la cuota de solidaridad a cargo del TRABAJADOR (reduce el neto).

    Cotización adicional sobre el salario que supera la base máxima mensual, en
    tres tramos. No existía antes de 2025 → 0. Devuelve 0 si el salario no supera
    el tope. Reparto trabajador ≈ 16,61 % (misma proporción que contingencias
    comunes), conforme a la definición legal.
    """
    base_salary = float(base_salary)
    tope = base_maxima_cotizacion(year)
    tipos = _CUOTA_SOLIDARIDAD_TIPOS.get(year if year is not None else _BASE_MAX_DEFAULT_YEAR)
    if tipos is None or base_salary <= tope:
        return 0.0
    total = 0.0
    for (mult_low, mult_high), tipo in zip(_SOLIDARIDAD_TRAMOS, tipos, strict=False):
        low = tope * mult_low
        high = tope * mult_high if mult_high is not None else float("inf")
        portion = min(base_salary, high) - low
        if portion > 0:
            total += portion * tipo * _SOLIDARIDAD_FRACCION_TRABAJADOR
    return round(total, 2)


VALID_CANDIDATE_STATUSES = {"new", "reviewed", "shortlisted", "rejected", "hired"}


# ── Calculo de nomina ────────────────────────────────────────────────────────


# Cotización del trabajador por horas extraordinarias (Régimen General):
# estructurales/normales 4,70 % · fuerza mayor 2,00 %.
_SS_HORAS_EXTRA = 0.0470
_SS_HORAS_EXTRA_FM = 0.0200

# Prestación IT por contingencias comunes (base reguladora diaria):
# días 1-3: 0 % · días 4-20: 60 % · día 21+: 75 % (salvo mejora de convenio).
_IT_TRAMOS = ((1, 3, 0.0), (4, 20, 0.60), (21, None, 0.75))

_DIAS_PERIODO = 30  # mes "comercial" usado como divisor de la base reguladora


def it_days_overlap(leave_start, leave_end, period_start, period_end) -> tuple[int, int]:
    """Días de baja IT que caen dentro del periodo de nómina.

    Devuelve ``(dias_it_en_periodo, dia_de_baja_al_inicio)``: cuántos días del
    periodo está de baja (máx. 30) y qué número de día de baja corresponde al
    primer día de IT dentro del periodo (para situar los tramos 60 %/75 %).
    """
    if not leave_start or not period_start or not period_end:
        return 0, 1
    start = max(leave_start, period_start)
    end = min(leave_end, period_end) if leave_end else period_end
    if start > end:
        return 0, 1
    dias = min((end - start).days + 1, _DIAS_PERIODO)
    dia_inicio = (start - leave_start).days + 1
    return dias, dia_inicio


def _prestacion_it(base_reguladora_diaria: float, dias_it: int, dia_inicio: int) -> float:
    """Prestación IT del periodo: suma día a día según el tramo legal."""
    total = 0.0
    for i in range(dias_it):
        dia = dia_inicio + i
        for low, high, pct in _IT_TRAMOS:
            if dia >= low and (high is None or dia <= high):
                total += base_reguladora_diaria * pct
                break
    return round(total, 2)


def calc_payroll(
    base_salary: float,
    irpf_rate: float,
    year: int | None = None,
    *,
    num_pagas: int = 12,
    prorratear_pagas: bool = False,
    jornada_pct: float = 100.0,
    horas_extra_importe: float = 0.0,
    horas_extra_fuerza_mayor: bool = False,
    dias_baja_it: int = 0,
    it_dia_inicio: int = 1,
) -> dict:
    """Calcula la nómina mensual: devengos, SS e IRPF del trabajador.

    Con los argumentos por defecto reproduce el cálculo clásico (mensualidad
    simple sobre el salario base). Los kwargs cubren los casos reales:

    - ``num_pagas``/``prorratear_pagas``: con 14 pagas, la prorrata de las
      extras SIEMPRE forma parte de la base de cotización mensual (art. 147
      LGSS); solo se suma al devengo si se prorratea en nómina.
    - ``jornada_pct``: jornada parcial — prorratea el salario base.
    - ``horas_extra_importe``: cotizan aparte (4,70 % trabajador; 2 % si son
      de fuerza mayor) y tributan IRPF como el resto del devengo.
    - ``dias_baja_it``/``it_dia_inicio``: baja por IT (contingencias comunes):
      días 1-3 sin prestación, 4-20 al 60 %, 21+ al 75 % de la base reguladora
      diaria (base/30). La cotización del mes se mantiene sobre la base normal.

    La SS se cotiza sobre la BASE DE COTIZACIÓN, topada por la base máxima
    mensual del año. El IRPF se retiene sobre el devengo íntegro, sin tope.
    `year`: año del periodo para elegir tope/MEI; si es None usa el más reciente.
    """
    base_salary = float(base_salary)
    irpf_rate = float(irpf_rate)

    # Jornada parcial: prorrateo del salario base.
    jornada_pct = float(jornada_pct or 100.0)
    base_mes = round(base_salary * jornada_pct / 100, 2)

    # Pagas extra: prorrata mensual (solo si hay más de 12 pagas).
    pagas_extra = max(int(num_pagas or 12) - 12, 0)
    prorrata_extra = round(base_mes * pagas_extra / 12, 2) if pagas_extra else 0.0

    # Baja IT: días trabajados cobran salario; días de baja cobran prestación.
    dias_baja_it = min(max(int(dias_baja_it or 0), 0), _DIAS_PERIODO)
    base_reguladora_diaria = round(base_mes / _DIAS_PERIODO, 4)
    salario_dias_trabajados = round(base_mes * (_DIAS_PERIODO - dias_baja_it) / _DIAS_PERIODO, 2)
    prestacion_it = (
        _prestacion_it(base_reguladora_diaria, dias_baja_it, max(int(it_dia_inicio or 1), 1)) if dias_baja_it else 0.0
    )

    horas_extra_importe = round(float(horas_extra_importe or 0.0), 2)

    # Devengo bruto del periodo.
    gross = round(
        salario_dias_trabajados + prestacion_it + (prorrata_extra if prorratear_pagas else 0.0) + horas_extra_importe,
        2,
    )

    # Base de cotización mensual: salario + prorrata de extras, topada.
    # Durante la IT la obligación de cotizar se mantiene sobre la base normal.
    tope = base_maxima_cotizacion(year)
    base_mensual = base_mes + prorrata_extra
    base_cotizacion = min(base_mensual, tope) if base_mensual > 0 else 0.0
    ss_cc = round(base_cotizacion * _SS_CONTINGENCIAS, 2)
    ss_des = round(base_cotizacion * _SS_DESEMPLEO, 2)
    ss_fp = round(base_cotizacion * _SS_FP, 2)
    ss_mei = round(base_cotizacion * mei_trabajador(year), 2)
    # Horas extra: cotización adicional del trabajador, fuera del tope mensual.
    tipo_he = _SS_HORAS_EXTRA_FM if horas_extra_fuerza_mayor else _SS_HORAS_EXTRA
    ss_horas_extra = round(horas_extra_importe * tipo_he, 2)
    total_ss = round(ss_cc + ss_des + ss_fp + ss_mei + ss_horas_extra, 2)

    irpf = round(gross * (irpf_rate / 100), 2)
    # Cuota de solidaridad del trabajador (solo si la base mensual supera el tope).
    solidaridad = cuota_solidaridad_trabajador(base_mensual, year)
    deductions = round(total_ss + irpf + solidaridad, 2)
    net = round(gross - deductions, 2)

    devengos = {
        "salario_base": salario_dias_trabajados,
        "prorrata_pagas_extra": prorrata_extra if prorratear_pagas else 0.0,
        "horas_extra": horas_extra_importe,
        "prestacion_it": prestacion_it,
        "dias_trabajados": _DIAS_PERIODO - dias_baja_it,
        "dias_baja_it": dias_baja_it,
        "num_pagas": int(num_pagas or 12),
        "jornada_pct": jornada_pct,
    }

    return {
        "gross_salary": gross,
        "devengos": devengos,
        "ss_contingencias_comunes": ss_cc,
        "ss_desempleo": ss_des,
        "ss_formacion_profesional": ss_fp,
        "ss_mei": ss_mei,
        "ss_horas_extra": ss_horas_extra,
        "total_ss": total_ss,
        "irpf": irpf,
        "cuota_solidaridad": solidaridad,
        "deductions": deductions,
        "net_salary": net,
        "base_cotizacion": round(base_cotizacion, 2),
    }


def calc_payroll_for_employee(
    emp: Employee,
    base_salary: float,
    irpf_rate: float,
    year: int | None = None,
    period_start=None,
    period_end=None,
    horas_extra_importe: float = 0.0,
) -> dict:
    """calc_payroll derivando los kwargs desde la ficha del empleado.

    - Jornada parcial: % desde ``jornada_horas_semana`` (sobre 40 h).
    - Pagas: ``num_pagas`` del empleado (12 por defecto).
    - Baja IT: si el empleado está de ``baja_medica`` y las fechas solapan
      el periodo de la nómina.
    """
    jornada_pct = 100.0
    if (emp.jornada_tipo or "completa") == "parcial" and emp.jornada_horas_semana:
        jornada_pct = round(float(emp.jornada_horas_semana) / 40.0 * 100, 2)

    dias_it, it_inicio = 0, 1
    if emp.leave_type == "baja_medica" and emp.leave_start and period_start and period_end:
        ps = period_start.date() if hasattr(period_start, "date") else period_start
        pe = period_end.date() if hasattr(period_end, "date") else period_end
        dias_it, it_inicio = it_days_overlap(emp.leave_start, emp.leave_end, ps, pe)

    return calc_payroll(
        base_salary,
        irpf_rate,
        year=year,
        num_pagas=int(getattr(emp, "num_pagas", None) or 12),
        prorratear_pagas=bool(getattr(emp, "prorratear_pagas", False)),
        jornada_pct=jornada_pct,
        horas_extra_importe=horas_extra_importe,
        dias_baja_it=dias_it,
        it_dia_inicio=it_inicio,
    )


# ── Employee queries ─────────────────────────────────────────────────────────


async def list_employees(tenant_id, db: AsyncSession) -> list[Employee]:
    result = await db.execute(
        select(Employee).where(Employee.tenant_id == tenant_id).order_by(desc(Employee.created_at))
    )
    return list(result.scalars().all())


async def get_employee(employee_id: UUID, tenant_id, db: AsyncSession) -> Employee | None:
    result = await db.execute(select(Employee).where(Employee.id == employee_id, Employee.tenant_id == tenant_id))
    return result.scalar_one_or_none()


# ── Document helpers (private) ───────────────────────────────────────────────


def _load_sepe_logo_b64() -> str:
    """Load SEPE logo as a data URI PNG for embedding in HTML."""
    candidates = [
        # Ubicación real del asset en el repo.
        os.path.join(os.path.dirname(__file__), "..", "assets", "sepe_logo.png"),
        # Rutas históricas conservadas por compatibilidad.
        os.path.join(os.path.dirname(__file__), "assets", "sepe_logo.png"),
        os.path.join(os.path.dirname(__file__), "..", "api", "v1", "routes", "assets", "sepe_logo.png"),
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
⚠️ AI ACT COMPLIANCE (Reglamento UE 2024/1689, Anexo III punto 4): esta plantilla
emite ÚNICAMENTE la estructura formal del documento. El LLM NO redacta el texto
motivado de la causa del despido. La motivación debe ser redactada y revisada
por un abogado laboralista. Ver docs/ai_act_scoping.md §2.

ESTRUCTURA CARTA DE DESPIDO (plantilla vacía, structure-only):

1. Cabecera empresa (razón social, NIF, domicilio).
2. Lugar y fecha.
3. Datos destinatario (trabajador: nombre, DNI/NIE, categoría).
4. PÁRRAFO VACÍO PARA LA MOTIVACIÓN — inserta literalmente el placeholder:
     "[INSERTAR AQUÍ LA MOTIVACIÓN DEL DESPIDO, REDACTADA Y REVISADA POR UN
      ABOGADO LABORALISTA. ESTE DOCUMENTO NO SE PUEDE ENTREGAR AL TRABAJADOR
      SIN COMPLETAR ESTE APARTADO.]"
   NO redactes texto motivado. NO menciones hechos del trabajador. NO sugieras
   causas. NO valores si encaja en Art. 52 o Art. 54 del Estatuto de los
   Trabajadores.
5. Marco legal genérico: incluye una referencia neutra a los Arts. 52 y 54
   del Estatuto de los Trabajadores como marco normativo, SIN aplicarlos al
   caso concreto. Ejemplo literal: "El presente despido se enmarca en los
   supuestos previstos por los artículos 52 y 54 del Real Decreto Legislativo
   2/2015, de 23 de octubre, por el que se aprueba el texto refundido de la
   Ley del Estatuto de los Trabajadores."
6. Efectos: placeholders para fecha de efectividad e indemnización.
   NO calcules indemnización automáticamente — placeholder
     "[FECHA EFECTIVIDAD: __/__/____]" y "[INDEMNIZACIÓN: __ días/año × __ años
     × salario base = __ €  — calcular con abogado]".
7. Firma empresa + lugar y fecha.
8. Disclaimer al pie (texto literal):
     "Este documento ha sido generado como plantilla formal por
      AutomatizaCore. La motivación de la causa de despido y los efectos
      económicos deben ser validados por un abogado laboralista antes de su
      entrega al trabajador. AutomatizaCore no asume responsabilidad sobre
      el contenido."

PROHIBIDO en este tipo de documento:
- Redactar la motivación de la causa del despido.
- Mencionar hechos, conducta o rendimiento específicos del trabajador.
- Sugerir o argumentar si la causa encaja en Art. 52 (objetivo) o Art. 54 (disciplinario).
- Calcular indemnización automáticamente.
- Valorar la procedencia o improcedencia del despido.
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


async def list_positions(db: AsyncSession, tenant_id: UUID, status_filter: str = "all") -> list[dict]:
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

    out = [
        {
            "id": p.id,
            "title": p.title,
            "department": p.department,
            "description": p.description,
            "required_skills": p.required_skills,
            "experience_min_years": float(p.experience_min_years) if p.experience_min_years else 0,
            "salary_range_min": float(p.salary_range_min) if p.salary_range_min else None,
            "salary_range_max": float(p.salary_range_max) if p.salary_range_max else None,
            "status": p.status,
            "candidate_count": counts.get(p.id, 0),
        }
        for p in positions
    ]
    return out


async def list_candidates(db: AsyncSession, tenant_id: UUID, position_id: UUID) -> list:
    # AI.SCO — orden cronológico inverso (no ranking por score).
    # Ver docs/ai_act_scoping.md §2 (Anexo III AI Act).
    result = await db.execute(
        select(Candidate)
        .where(
            Candidate.tenant_id == tenant_id,
            Candidate.position_id == position_id,
        )
        .order_by(Candidate.created_at.desc())
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

    target = date or local_today()
    result = await db.execute(
        select(Attendance)
        .where(Attendance.tenant_id == tenant_id, Attendance.date == target)
        .order_by(Attendance.clock_in)
    )
    return [_attendance_row(r) for r in result.scalars().all()]


async def attendance_summary(db: AsyncSession, tenant_id, desde, hasta) -> list[dict]:
    """Horas fichadas por empleado en el rango [desde, hasta] (ambos inclusive).

    Suma solo los tramos CERRADOS (con `clock_out`); los abiertos se cuentan
    aparte (`abiertos`) para que un fichaje olvidado no infle las horas.
    Devuelve una fila por empleado ordenada por horas descendentes."""
    result = await db.execute(
        select(Attendance).where(
            Attendance.tenant_id == tenant_id,
            Attendance.date >= desde,
            Attendance.date <= hasta,
        )
    )
    por_emp: dict[str, dict] = {}
    for r in result.scalars().all():
        acc = por_emp.setdefault(
            str(r.employee_id),
            {"employee_id": str(r.employee_id), "minutos": 0, "_dias": set(), "tramos": 0, "abiertos": 0},
        )
        if r.clock_out is not None:
            delta_min = (r.clock_out - r.clock_in).total_seconds() / 60
            if delta_min > 0:
                acc["minutos"] += int(delta_min)
            acc["tramos"] += 1
            acc["_dias"].add(str(r.date))
        else:
            acc["abiertos"] += 1
    filas = []
    for acc in por_emp.values():
        dias = len(acc.pop("_dias"))
        filas.append({**acc, "dias": dias, "horas": round(acc["minutos"] / 60, 2)})
    filas.sort(key=lambda f: f["minutos"], reverse=True)
    return filas


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


async def list_leave_requests(db: AsyncSession, tenant_id, status_filter: str | None = None) -> list[dict]:
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


async def list_expenses(db: AsyncSession, tenant_id, status_filter: str | None = None, employee_id=None) -> list[dict]:
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
    result = await db.execute(select(Expense).where(Expense.id == expense_id, Expense.tenant_id == tenant_id))
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
