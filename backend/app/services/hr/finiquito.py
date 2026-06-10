"""Cálculo de finiquito — liquidación al término de la relación laboral.

Conceptos calculados (Estatuto de los Trabajadores):
- Vacaciones devengadas y no disfrutadas (cotizan y tributan).
- Prorrata de pagas extra devengada y no cobrada (si no se prorratea en nómina).
- Indemnización según causa de extinción: despido objetivo 20 días/año (tope
  12 mensualidades), improcedente 33 días/año (tope 24), fin de contrato
  temporal 12 días/año. Baja voluntaria / mutuo acuerdo / jubilación: 0.

Simplificaciones documentadas: la indemnización se considera exenta de IRPF y
de cotización (art. 7.e LIRPF, dentro de los límites legales); el devengo de
las pagas extra se prorratea linealmente sobre el año natural.
"""

from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.hr import Settlement
from app.db.models.models import Employee
from app.services.hr.queries import (
    _SS_CONTINGENCIAS,
    _SS_DESEMPLEO,
    _SS_FP,
    mei_trabajador,
)

# causa → (días de indemnización por año trabajado, tope en mensualidades)
_INDEMNIZACION = {
    "despido_objetivo": (20, 12),
    "despido_improcedente": (33, 24),
    "fin_contrato": (12, None),
}

_DIAS_MES = 30


def _parse_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _normalize_causa(causa: str) -> str:
    c = (causa or "").strip().lower().replace(" ", "_")
    if "improcedente" in c:
        return "despido_improcedente"
    if "objetivo" in c or "despido" == c:
        return "despido_objetivo"
    if "fin" in c and "contrato" in c:
        return "fin_contrato"
    if "voluntaria" in c or "dimision" in c or "dimisión" in c:
        return "baja_voluntaria"
    if "mutuo" in c:
        return "mutuo_acuerdo"
    if "jubilacion" in c or "jubilación" in c:
        return "jubilacion"
    return c or "baja_voluntaria"


def calc_finiquito(
    *,
    base_salary: float,
    irpf_rate: float = 15.0,
    num_pagas: int = 12,
    prorratear_pagas: bool = False,
    fecha_alta=None,
    fecha_baja,
    causa: str = "baja_voluntaria",
    vacaciones_pendientes_dias: float = 0.0,
    year: int | None = None,
) -> dict:
    """Calcula el finiquito. Devuelve desglose, totales y conceptos para PDF."""
    base_salary = float(base_salary or 0)
    f_baja = _parse_date(fecha_baja)
    f_alta = _parse_date(fecha_alta)
    causa_norm = _normalize_causa(causa)

    salario_diario = round(base_salary / _DIAS_MES, 4)

    # Vacaciones no disfrutadas
    vac_dias = max(float(vacaciones_pendientes_dias or 0), 0.0)
    vacaciones_importe = round(vac_dias * salario_diario, 2)

    # Prorrata de pagas extra devengada (devengo lineal sobre el año natural).
    pagas_extra = max(int(num_pagas or 12) - 12, 0)
    prorrata_extra = 0.0
    if pagas_extra and not prorratear_pagas and f_baja:
        dia_anyo = f_baja.timetuple().tm_yday
        prorrata_extra = round(base_salary * pagas_extra * dia_anyo / 365, 2)

    # Indemnización por causa de extinción
    indemnizacion = 0.0
    dias_anio, tope_mensualidades = _INDEMNIZACION.get(causa_norm, (0, None))
    if dias_anio and f_alta and f_baja and f_baja > f_alta:
        anios_servicio = (f_baja - f_alta).days / 365.25
        # Salario diario a efectos de indemnización: retribución anual / 365
        salario_anual = base_salary * max(int(num_pagas or 12), 12)
        salario_diario_indem = salario_anual / 365
        indemnizacion = dias_anio * anios_servicio * salario_diario_indem
        if tope_mensualidades:
            tope = tope_mensualidades * (salario_anual / 12)
            indemnizacion = min(indemnizacion, tope)
        indemnizacion = round(indemnizacion, 2)

    # Deducciones: solo sobre los conceptos salariales (no la indemnización).
    base_sujeta = round(vacaciones_importe + prorrata_extra, 2)
    tipo_ss = _SS_CONTINGENCIAS + _SS_DESEMPLEO + _SS_FP + mei_trabajador(year)
    deduccion_ss = round(base_sujeta * tipo_ss, 2)
    deduccion_irpf = round(base_sujeta * float(irpf_rate or 0) / 100, 2)

    total_percepciones = round(vacaciones_importe + prorrata_extra + indemnizacion, 2)
    total_deducciones = round(deduccion_ss + deduccion_irpf, 2)
    total_liquido = round(total_percepciones - total_deducciones, 2)

    conceptos = []
    if vacaciones_importe:
        conceptos.append(
            {"concepto": f"Vacaciones no disfrutadas ({vac_dias:g} días)", "importe": vacaciones_importe}
        )
    if prorrata_extra:
        conceptos.append({"concepto": "Prorrata pagas extra devengada", "importe": prorrata_extra})
    if indemnizacion:
        conceptos.append(
            {"concepto": f"Indemnización ({dias_anio} días/año)", "importe": indemnizacion}
        )
    if deduccion_ss:
        conceptos.append({"concepto": "Seguridad Social (deducción)", "importe": -deduccion_ss})
    if deduccion_irpf:
        conceptos.append({"concepto": f"IRPF {float(irpf_rate):g}% (deducción)", "importe": -deduccion_irpf})

    return {
        "causa": causa_norm,
        "fecha_baja": f_baja.isoformat() if f_baja else None,
        "vacaciones_pendientes_dias": vac_dias,
        "vacaciones_pendientes_importe": vacaciones_importe,
        "prorrata_paga_extra": prorrata_extra,
        "indemnizacion": indemnizacion,
        "deduccion_ss": deduccion_ss,
        "deduccion_irpf": deduccion_irpf,
        "total_percepciones": total_percepciones,
        "total_deducciones": total_deducciones,
        "total_liquido": total_liquido,
        "conceptos": conceptos,
    }


def calc_finiquito_for_employee(
    emp: Employee,
    fecha_baja,
    causa: str,
    vacaciones_pendientes_dias: float = 0.0,
) -> dict:
    """calc_finiquito derivando salario, IRPF, pagas y antigüedad de la ficha."""
    f_baja = _parse_date(fecha_baja)
    return calc_finiquito(
        base_salary=float(emp.base_salary or 0),
        irpf_rate=float(emp.irpf_rate or 15.0),
        num_pagas=int(getattr(emp, "num_pagas", None) or 12),
        prorratear_pagas=bool(getattr(emp, "prorratear_pagas", False)),
        fecha_alta=emp.join_date,
        fecha_baja=fecha_baja,
        causa=causa,
        vacaciones_pendientes_dias=vacaciones_pendientes_dias,
        year=f_baja.year if f_baja else None,
    )


async def create_settlement(
    db: AsyncSession,
    tenant_id,
    employee_id,
    calc: dict,
) -> Settlement:
    """Persiste el finiquito calculado como Settlement (estado draft)."""
    f_baja = _parse_date(calc.get("fecha_baja")) or date.today()
    settlement = Settlement(
        tenant_id=tenant_id,
        employee_id=employee_id,
        fecha_extincion=datetime(f_baja.year, f_baja.month, f_baja.day, tzinfo=UTC),
        causa_extincion=calc["causa"],
        vacaciones_pendientes_dias=calc["vacaciones_pendientes_dias"],
        vacaciones_pendientes_importe=calc["vacaciones_pendientes_importe"],
        prorrata_paga_extra=calc["prorrata_paga_extra"],
        indemnizacion=calc["indemnizacion"],
        total_percepciones=calc["total_percepciones"],
        deduccion_ss=calc["deduccion_ss"],
        deduccion_irpf=calc["deduccion_irpf"],
        total_deducciones=calc["total_deducciones"],
        total_liquido=calc["total_liquido"],
        status="draft",
    )
    db.add(settlement)
    await db.commit()
    await db.refresh(settlement)
    return settlement
