"""Agregación de datos para modelos AEAT 130, 347 y 390 (MOD.130 / MOD.347 / MOD.390).

Cada función devuelve un dict listo para PDF/CSV. La especificación de campos
oficiales (etiquetas, casillas) se ajustará en una capa de presentación
posterior — aquí solo agregamos los importes con las reglas legales.

Referencias normativas:
- Modelo 130: Orden HAC/1264/2018 — IRPF fraccionado estimación directa.
- Modelo 347: Real Decreto 1065/2007 Art. 32 — umbral 3.005,06€/año.
- Modelo 390: Orden HAC/1351/2014 — resumen anual IVA.
"""

from calendar import monthrange
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload as jl

from app.db.models.models import Invoice, Payroll, Tenant
from app.db.models.crm import Client
from app.db.models.hr import Employee


# Umbral legal del Modelo 347 (operaciones con terceros).
MODELO_347_THRESHOLD = Decimal("3005.06")


async def _get_tenant_info(db: AsyncSession, tenant_id: UUID) -> tuple[str, str]:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        return ("Mi Empresa", "B00000000")
    return (tenant.name or "Mi Empresa", tenant.nif or "B00000000")


async def _invoices_in_period(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    invoice_type: str,
    start: date,
    end: date,
) -> list[Invoice]:
    q = await db.execute(
        select(Invoice)
        .options(jl(Invoice.lines))
        .where(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.invoice_type == invoice_type,
                func.date(Invoice.date) >= start,
                func.date(Invoice.date) <= end,
            )
        )
    )
    return list(q.unique().scalars().all())


# ─────────────────────────────────────────────────────────────────────────────
# Modelo 130 — IRPF fraccionado estimación directa
# ─────────────────────────────────────────────────────────────────────────────


async def build_modelo_130_data(
    db: AsyncSession,
    tenant_id: UUID,
    quarter: int,
    year: int,
) -> dict[str, Any]:
    """Agrega datos para el Modelo 130 (IRPF fraccionado, estimación directa).

    Cálculo simplificado (MVP):
    - Ingresos acumulados del año hasta fin del trimestre (ventas emitidas).
    - Gastos deducibles acumulados (facturas recibidas).
    - Beneficio = Ingresos - Gastos.
    - Pago fraccionado = 20% sobre el beneficio acumulado, menos lo ya pagado
      en trimestres anteriores y menos retenciones soportadas.

    El cálculo final del Modelo 130 tiene matices (mínimo personal/familiar,
    correctores) que requieren datos del contribuyente fuera del scope MVP.
    """
    if quarter not in (1, 2, 3, 4):
        raise ValueError("quarter debe ser 1, 2, 3 o 4")

    quarter_months = {1: 3, 2: 6, 3: 9, 4: 12}
    start = date(year, 1, 1)
    last_month = quarter_months[quarter]
    end = date(year, last_month, monthrange(year, last_month)[1])

    tenant_name, tenant_nif = await _get_tenant_info(db, tenant_id)

    issued = await _invoices_in_period(db, tenant_id, invoice_type="issued", start=start, end=end)
    received = await _invoices_in_period(db, tenant_id, invoice_type="received", start=start, end=end)

    ingresos = sum((Decimal(inv.amount_base or 0) for inv in issued), Decimal("0"))
    gastos = sum((Decimal(inv.amount_base or 0) for inv in received), Decimal("0"))
    beneficio = ingresos - gastos

    pago_fraccionado_bruto = (beneficio * Decimal("0.20")).quantize(Decimal("0.01"))
    if pago_fraccionado_bruto < 0:
        pago_fraccionado_bruto = Decimal("0.00")

    return {
        "modelo": "130",
        "ejercicio": year,
        "periodo": f"{quarter}T",
        "tenant": {"name": tenant_name, "nif": tenant_nif},
        "ingresos_acumulados": float(ingresos),
        "gastos_acumulados": float(gastos),
        "beneficio_acumulado": float(beneficio),
        "pago_fraccionado_bruto": float(pago_fraccionado_bruto),
        # Las siguientes casillas requieren datos cross-period que aquí se
        # dejan al usuario por simplicidad MVP — el wizard fiscal las completa.
        "retenciones_soportadas": 0.0,
        "pagos_fraccionados_anteriores": 0.0,
        "resultado_a_ingresar": float(pago_fraccionado_bruto),
        "num_facturas_emitidas": len(issued),
        "num_facturas_recibidas": len(received),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Modelo 347 — operaciones con terceros >3.005,06€/año
# ─────────────────────────────────────────────────────────────────────────────


async def build_modelo_347_data(
    db: AsyncSession,
    tenant_id: UUID,
    year: int,
) -> dict[str, Any]:
    """Agrega datos para el Modelo 347 (operaciones con terceros, umbral 3.005,06€).

    Agrupa por NIF de cliente/proveedor las facturas emitidas y recibidas del
    año natural completo. Devuelve únicamente las contrapartes cuyo importe
    agregado supere el umbral legal de 3.005,06€.
    """
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    tenant_name, tenant_nif = await _get_tenant_info(db, tenant_id)

    # Mapeamos NIF → (nombre, importe_emitidas, importe_recibidas)
    by_nif: dict[str, dict[str, Any]] = {}

    issued = await _invoices_in_period(db, tenant_id, invoice_type="issued", start=start, end=end)
    for inv in issued:
        client_q = await db.execute(select(Client).where(Client.id == inv.client_id))
        client = client_q.scalar_one_or_none()
        nif = (client.nif if client else None) or "SIN_NIF"
        name = (client.name if client else "Cliente desconocido")
        entry = by_nif.setdefault(nif, {"nif": nif, "nombre": name, "emitidas": Decimal("0"), "recibidas": Decimal("0")})
        entry["emitidas"] += Decimal(inv.amount_total or 0)

    received = await _invoices_in_period(db, tenant_id, invoice_type="received", start=start, end=end)
    for inv in received:
        # Para facturas recibidas, el "tercero" es el proveedor. Reutilizamos client_id
        # porque en el modelo actual la contraparte vive en la misma tabla `clients`.
        client_q = await db.execute(select(Client).where(Client.id == inv.client_id))
        client = client_q.scalar_one_or_none()
        nif = (client.nif if client else None) or "SIN_NIF"
        name = (client.name if client else "Proveedor desconocido")
        entry = by_nif.setdefault(nif, {"nif": nif, "nombre": name, "emitidas": Decimal("0"), "recibidas": Decimal("0")})
        entry["recibidas"] += Decimal(inv.amount_total or 0)

    declarables = []
    for entry in by_nif.values():
        emitidas = entry["emitidas"]
        recibidas = entry["recibidas"]
        if max(emitidas, recibidas) >= MODELO_347_THRESHOLD:
            declarables.append({
                "nif": entry["nif"],
                "nombre": entry["nombre"],
                "importe_emitidas": float(emitidas),
                "importe_recibidas": float(recibidas),
            })

    declarables.sort(key=lambda d: d["nif"])

    return {
        "modelo": "347",
        "ejercicio": year,
        "tenant": {"name": tenant_name, "nif": tenant_nif},
        "umbral_legal": float(MODELO_347_THRESHOLD),
        "num_declarables": len(declarables),
        "declarables": declarables,
        "total_contrapartes_analizadas": len(by_nif),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Modelo 111 — retenciones IRPF trimestrales
# ─────────────────────────────────────────────────────────────────────────────


async def _payrolls_in_period(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    start: date,
    end: date,
) -> list[Payroll]:
    q = await db.execute(
        select(Payroll).where(
            and_(
                Payroll.tenant_id == tenant_id,
                func.date(Payroll.period_start) >= start,
                func.date(Payroll.period_start) <= end,
            )
        )
    )
    return list(q.scalars().all())


async def build_modelo_111_data(
    db: AsyncSession,
    tenant_id: UUID,
    quarter: int,
    year: int,
) -> dict[str, Any]:
    """Agrega datos para el Modelo 111 (retenciones IRPF trimestrales).

    Suma las retenciones IRPF practicadas sobre nóminas del trimestre.
    Las retenciones a profesionales (Art. 95 LIRPF, 15% sobre facturas)
    requieren un campo `retencion_irpf` en `Invoice` que no existe en el
    esquema actual — se documenta como TODO v1.1.

    Cálculo:
    - Suma de `Payroll.base_irpf` → base retenciones del personal.
    - Suma de `Payroll.irpf` → retenciones practicadas.
    - Agrupado por empleado para detalle perceptor.
    """
    if quarter not in (1, 2, 3, 4):
        raise ValueError("quarter debe ser 1, 2, 3 o 4")

    quarter_months = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
    m_start, m_end = quarter_months[quarter]
    start = date(year, m_start, 1)
    end = date(year, m_end, monthrange(year, m_end)[1])

    tenant_name, tenant_nif = await _get_tenant_info(db, tenant_id)
    payrolls = await _payrolls_in_period(db, tenant_id, start=start, end=end)

    # Agrupar por empleado
    by_employee: dict[Any, dict[str, Any]] = {}
    for p in payrolls:
        emp_id = p.employee_id
        entry = by_employee.setdefault(
            emp_id,
            {
                "employee_id": str(emp_id) if emp_id else None,
                "nombre": None,
                "nif": None,
                "base_retencion": Decimal("0"),
                "retencion_practicada": Decimal("0"),
                "num_nominas": 0,
            },
        )
        entry["base_retencion"] += Decimal(p.base_irpf or 0)
        entry["retencion_practicada"] += Decimal(p.irpf or 0)
        entry["num_nominas"] += 1

    # Enriquecer con datos del empleado
    if by_employee:
        emp_q = await db.execute(
            select(Employee).where(Employee.id.in_(list(by_employee.keys())))
        )
        for emp in emp_q.scalars().all():
            entry = by_employee.get(emp.id)
            if entry is not None:
                entry["nombre"] = emp.name
                entry["nif"] = emp.nif

    perceptores = [
        {
            "employee_id": e["employee_id"],
            "nombre": e["nombre"],
            "nif": e["nif"],
            "base_retencion": float(e["base_retencion"]),
            "retencion_practicada": float(e["retencion_practicada"]),
            "num_nominas": e["num_nominas"],
        }
        for e in by_employee.values()
    ]
    perceptores.sort(key=lambda p: (p["nif"] or "", p["nombre"] or ""))

    total_base = sum(Decimal(str(p["base_retencion"])) for p in perceptores)
    total_retencion = sum(Decimal(str(p["retencion_practicada"])) for p in perceptores)

    return {
        "modelo": "111",
        "ejercicio": year,
        "periodo": f"{quarter}T",
        "tenant": {"name": tenant_name, "nif": tenant_nif},
        "perceptores_trabajo_personal": perceptores,
        "total_base_retenciones": float(total_base),
        "total_retencion_practicada": float(total_retencion),
        "num_perceptores": len(perceptores),
        # TODO v1.1: incluir retenciones a profesionales cuando se añada
        # `retencion_irpf` en `Invoice` (Art. 95 LIRPF, 15% facturas recibidas
        # de profesionales con NIF que opten por retención).
        "perceptores_profesionales": [],
        "_pending_v1_1": "retenciones a profesionales (Art. 95 LIRPF)",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Modelo 190 — resumen anual de retenciones (4 × Modelo 111)
# ─────────────────────────────────────────────────────────────────────────────


async def build_modelo_190_data(
    db: AsyncSession,
    tenant_id: UUID,
    year: int,
) -> dict[str, Any]:
    """Agrega datos para el Modelo 190 (resumen anual retenciones IRPF).

    Es la consolidación anual del Modelo 111: suma de retenciones practicadas
    durante todo el año, agrupadas por perceptor con clave de percepción.
    Para MVP usamos clave "A" (rendimientos del trabajo) para todos los
    empleados; las claves G (actividades profesionales) y K (premios) requieren
    los campos de retención en `Invoice` pendientes para v1.1.
    """
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    tenant_name, tenant_nif = await _get_tenant_info(db, tenant_id)
    payrolls = await _payrolls_in_period(db, tenant_id, start=start, end=end)

    by_employee: dict[Any, dict[str, Any]] = {}
    for p in payrolls:
        emp_id = p.employee_id
        entry = by_employee.setdefault(
            emp_id,
            {
                "employee_id": str(emp_id) if emp_id else None,
                "clave_percepcion": "A",  # rendimientos del trabajo
                "nombre": None,
                "nif": None,
                "percepcion_integra": Decimal("0"),
                "retencion_practicada": Decimal("0"),
                "num_nominas": 0,
            },
        )
        # Percepción íntegra ≈ base IRPF (sin SS empresa). Aproximación MVP.
        entry["percepcion_integra"] += Decimal(p.base_irpf or 0)
        entry["retencion_practicada"] += Decimal(p.irpf or 0)
        entry["num_nominas"] += 1

    if by_employee:
        emp_q = await db.execute(
            select(Employee).where(Employee.id.in_(list(by_employee.keys())))
        )
        for emp in emp_q.scalars().all():
            entry = by_employee.get(emp.id)
            if entry is not None:
                entry["nombre"] = emp.name
                entry["nif"] = emp.nif

    perceptores = [
        {
            "clave_percepcion": e["clave_percepcion"],
            "employee_id": e["employee_id"],
            "nombre": e["nombre"],
            "nif": e["nif"],
            "percepcion_integra": float(e["percepcion_integra"]),
            "retencion_practicada": float(e["retencion_practicada"]),
            "num_nominas": e["num_nominas"],
        }
        for e in by_employee.values()
    ]
    perceptores.sort(key=lambda p: (p["clave_percepcion"], p["nif"] or ""))

    total_percepcion = sum(Decimal(str(p["percepcion_integra"])) for p in perceptores)
    total_retencion = sum(Decimal(str(p["retencion_practicada"])) for p in perceptores)

    return {
        "modelo": "190",
        "ejercicio": year,
        "tenant": {"name": tenant_name, "nif": tenant_nif},
        "perceptores": perceptores,
        "num_perceptores": len(perceptores),
        "total_percepcion_integra": float(total_percepcion),
        "total_retencion_practicada": float(total_retencion),
        "_pending_v1_1": "claves G/K (profesionales/premios) — requiere retencion_irpf en Invoice",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Modelo 390 — resumen anual IVA
# ─────────────────────────────────────────────────────────────────────────────


async def build_modelo_390_data(
    db: AsyncSession,
    tenant_id: UUID,
    year: int,
) -> dict[str, Any]:
    """Agrega datos para el Modelo 390 (resumen anual IVA).

    Es la suma anual de los 4 trimestres del 303: IVA devengado (ventas) e
    IVA deducible (compras) agregados por tipo impositivo.
    """
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    tenant_name, tenant_nif = await _get_tenant_info(db, tenant_id)

    issued = await _invoices_in_period(db, tenant_id, invoice_type="issued", start=start, end=end)
    received = await _invoices_in_period(db, tenant_id, invoice_type="received", start=start, end=end)

    devengado: dict[float, dict[str, float]] = {}
    deducible: dict[float, dict[str, float]] = {}

    for inv in issued:
        for line in inv.lines or []:
            rate = float(line.tax_percentage or 21)
            base = float(line.quantity or 1) * float(line.unit_price or 0)
            if line.discount_percentage:
                base -= base * float(line.discount_percentage) / 100
            quota = base * rate / 100
            entry = devengado.setdefault(rate, {"rate": rate, "base": 0.0, "quota": 0.0})
            entry["base"] += base
            entry["quota"] += quota

    for inv in received:
        for line in inv.lines or []:
            rate = float(line.tax_percentage or 21)
            base = float(line.quantity or 1) * float(line.unit_price or 0)
            if line.discount_percentage:
                base -= base * float(line.discount_percentage) / 100
            quota = base * rate / 100
            entry = deducible.setdefault(rate, {"rate": rate, "base": 0.0, "quota": 0.0})
            entry["base"] += base
            entry["quota"] += quota

    total_devengado = sum(e["quota"] for e in devengado.values())
    total_deducible = sum(e["quota"] for e in deducible.values())
    resultado = total_devengado - total_deducible

    return {
        "modelo": "390",
        "ejercicio": year,
        "tenant": {"name": tenant_name, "nif": tenant_nif},
        "iva_devengado": sorted(devengado.values(), key=lambda x: x["rate"]),
        "iva_deducible": sorted(deducible.values(), key=lambda x: x["rate"]),
        "total_devengado": round(total_devengado, 2),
        "total_deducible": round(total_deducible, 2),
        "resultado_anual": round(resultado, 2),
        "num_facturas_emitidas": len(issued),
        "num_facturas_recibidas": len(received),
    }
