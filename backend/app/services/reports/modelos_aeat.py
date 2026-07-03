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
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload as jl

from app.db.models.crm import Client
from app.db.models.hr import Employee
from app.db.models.models import Invoice, Payroll, Tenant
from app.services.billing.constants import EMITTED_INVOICE_TYPES

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
    # Invariante fiscal (N1/N2, 2026-06-25): el lado emitido incluye las
    # rectificativas (abono, importes negados → minoran el devengado) y se
    # excluyen las anuladas ('cancelled') para cuadrar con el libro registro.
    # Los borradores SÍ cuentan (las compras nacen 'draft').
    type_clause = (
        Invoice.invoice_type.in_(EMITTED_INVOICE_TYPES)
        if invoice_type == "issued"
        else Invoice.invoice_type == invoice_type
    )
    q = await db.execute(
        select(Invoice)
        .options(jl(Invoice.lines))
        .where(
            and_(
                Invoice.tenant_id == tenant_id,
                type_clause,
                Invoice.is_demo.is_(False),  # datos demo del onboarding NUNCA en fiscal
                Invoice.status.notin_(["cancelled"]),
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

    pago_fraccionado_bruto = (beneficio * Decimal("0.20")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if pago_fraccionado_bruto < 0:
        pago_fraccionado_bruto = Decimal("0.00")

    # N4: retenciones de IRPF que los clientes han practicado sobre las facturas
    # EMITIDAS (acumuladas desde el 1-ene) → casilla 06; reducen el pago fraccionado.
    retenciones = sum((Decimal(inv.retencion_irpf_amount or 0) for inv in issued), Decimal("0"))
    resultado = pago_fraccionado_bruto - retenciones
    if resultado < 0:
        resultado = Decimal("0.00")

    return {
        "modelo": "130",
        "ejercicio": year,
        "periodo": f"{quarter}T",
        "tenant": {"name": tenant_name, "nif": tenant_nif},
        "ingresos_acumulados": float(ingresos),
        "gastos_acumulados": float(gastos),
        "beneficio_acumulado": float(beneficio),
        "pago_fraccionado_bruto": float(pago_fraccionado_bruto),
        "retenciones_soportadas": float(retenciones),
        # pagos_fraccionados_anteriores es cross-period (130 ya presentados este
        # ejercicio): no derivable de facturas, lo completa el wizard fiscal.
        "pagos_fraccionados_anteriores": 0.0,
        "resultado_a_ingresar": float(resultado),
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
    received = await _invoices_in_period(db, tenant_id, invoice_type="received", start=start, end=end)

    # Cargamos todos los clientes/proveedores en UNA query (evita N+1).
    client_ids = {inv.client_id for inv in issued + received if inv.client_id}
    clients_by_id: dict[Any, Client] = {}
    if client_ids:
        cq = await db.execute(select(Client).where(Client.id.in_(client_ids)))
        clients_by_id = {c.id: c for c in cq.scalars().all()}

    for inv in issued:
        client = clients_by_id.get(inv.client_id)
        nif = (client.nif if client else None) or "SIN_NIF"
        name = client.name if client else "Cliente desconocido"
        entry = by_nif.setdefault(
            nif, {"nif": nif, "nombre": name, "emitidas": Decimal("0"), "recibidas": Decimal("0")}
        )
        entry["emitidas"] += Decimal(inv.amount_total or 0)

    for inv in received:
        # Para facturas recibidas, el "tercero" es el proveedor. Reutilizamos client_id
        # porque en el modelo actual la contraparte vive en la misma tabla `clients`.
        client = clients_by_id.get(inv.client_id)
        nif = (client.nif if client else None) or "SIN_NIF"
        name = client.name if client else "Proveedor desconocido"
        entry = by_nif.setdefault(
            nif, {"nif": nif, "nombre": name, "emitidas": Decimal("0"), "recibidas": Decimal("0")}
        )
        entry["recibidas"] += Decimal(inv.amount_total or 0)

    declarables = []
    for entry in by_nif.values():
        emitidas = entry["emitidas"]
        recibidas = entry["recibidas"]
        if max(emitidas, recibidas) >= MODELO_347_THRESHOLD:
            declarables.append(
                {
                    "nif": entry["nif"],
                    "nombre": entry["nombre"],
                    "importe_emitidas": float(emitidas),
                    "importe_recibidas": float(recibidas),
                }
            )

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
        emp_q = await db.execute(select(Employee).where(Employee.id.in_(list(by_employee.keys()))))
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

    # Retenciones a profesionales (Art. 95 LIRPF): facturas recibidas con
    # retención IRPF, agrupadas por proveedor.
    prof_q = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.invoice_type == "received",
                Invoice.is_demo.is_(False),  # datos demo del onboarding NUNCA en fiscal
                Invoice.status.notin_(["cancelled"]),  # N1: anuladas fuera del modelo
                Invoice.retencion_irpf_amount.isnot(None),
                Invoice.retencion_irpf_amount > 0,
                func.date(Invoice.date) >= start,
                func.date(Invoice.date) <= end,
            )
        )
    )
    prof_invoices = list(prof_q.scalars().all())

    by_supplier: dict[Any, dict[str, Any]] = {}
    for inv in prof_invoices:
        entry = by_supplier.setdefault(
            inv.client_id,
            {
                "client_id": str(inv.client_id),
                "nombre": None,
                "nif": None,
                "base_retencion": Decimal("0"),
                "retencion_practicada": Decimal("0"),
                "num_facturas": 0,
            },
        )
        entry["base_retencion"] += Decimal(inv.amount_base or 0)
        entry["retencion_practicada"] += Decimal(inv.retencion_irpf_amount or 0)
        entry["num_facturas"] += 1

    if by_supplier:
        cli_q = await db.execute(select(Client).where(Client.id.in_(list(by_supplier.keys()))))
        for cli in cli_q.scalars().all():
            entry = by_supplier.get(cli.id)
            if entry is not None:
                entry["nombre"] = cli.name
                entry["nif"] = getattr(cli, "nif", None)

    profesionales = [
        {
            "client_id": e["client_id"],
            "nombre": e["nombre"],
            "nif": e["nif"],
            "base_retencion": float(e["base_retencion"]),
            "retencion_practicada": float(e["retencion_practicada"]),
            "num_facturas": e["num_facturas"],
        }
        for e in by_supplier.values()
    ]
    profesionales.sort(key=lambda p: (p["nif"] or "", p["nombre"] or ""))

    total_base_prof = sum(Decimal(str(p["base_retencion"])) for p in profesionales)
    total_ret_prof = sum(Decimal(str(p["retencion_practicada"])) for p in profesionales)

    total_base = sum(Decimal(str(p["base_retencion"])) for p in perceptores) + total_base_prof
    total_retencion = sum(Decimal(str(p["retencion_practicada"])) for p in perceptores) + total_ret_prof

    return {
        "modelo": "111",
        "ejercicio": year,
        "periodo": f"{quarter}T",
        "tenant": {"name": tenant_name, "nif": tenant_nif},
        "perceptores_trabajo_personal": perceptores,
        "perceptores_profesionales": profesionales,
        "total_base_profesionales": float(total_base_prof),
        "total_retencion_profesionales": float(total_ret_prof),
        "total_base_retenciones": float(total_base),
        "total_retencion_practicada": float(total_retencion),
        "num_perceptores": len(perceptores) + len(profesionales),
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
    Incluye clave "A" (rendimientos del trabajo, desde nóminas) y clave "G"
    (actividades profesionales, desde facturas recibidas con retención IRPF —
    Art. 95 LIRPF). La clave K (premios) queda fuera de alcance por no existir
    todavía un modelo de datos de premios.
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
        emp_q = await db.execute(select(Employee).where(Employee.id.in_(list(by_employee.keys()))))
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
    # Clave G — actividades profesionales (Art. 95 LIRPF): facturas recibidas
    # con retención IRPF durante todo el año, agrupadas por proveedor.
    prof_q = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.invoice_type == "received",
                Invoice.is_demo.is_(False),  # datos demo del onboarding NUNCA en fiscal
                Invoice.status.notin_(["cancelled"]),  # N1: anuladas fuera del modelo
                Invoice.retencion_irpf_amount.isnot(None),
                Invoice.retencion_irpf_amount > 0,
                func.date(Invoice.date) >= start,
                func.date(Invoice.date) <= end,
            )
        )
    )
    by_supplier: dict[Any, dict[str, Any]] = {}
    for inv in prof_q.scalars().all():
        entry = by_supplier.setdefault(
            inv.client_id,
            {
                "clave_percepcion": "G",  # actividades profesionales
                "client_id": str(inv.client_id),
                "nombre": None,
                "nif": None,
                "percepcion_integra": Decimal("0"),
                "retencion_practicada": Decimal("0"),
                "num_facturas": 0,
            },
        )
        entry["percepcion_integra"] += Decimal(inv.amount_base or 0)
        entry["retencion_practicada"] += Decimal(inv.retencion_irpf_amount or 0)
        entry["num_facturas"] += 1

    if by_supplier:
        cli_q = await db.execute(select(Client).where(Client.id.in_(list(by_supplier.keys()))))
        for cli in cli_q.scalars().all():
            entry = by_supplier.get(cli.id)
            if entry is not None:
                entry["nombre"] = cli.name
                entry["nif"] = getattr(cli, "nif", None)

    perceptores.extend(
        {
            "clave_percepcion": e["clave_percepcion"],
            "client_id": e["client_id"],
            "nombre": e["nombre"],
            "nif": e["nif"],
            "percepcion_integra": float(e["percepcion_integra"]),
            "retencion_practicada": float(e["retencion_practicada"]),
            "num_facturas": e["num_facturas"],
        }
        for e in by_supplier.values()
    )

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

    # Mismo desglose Decimal que el 303 trimestral → el 390 anual cuadra con la
    # suma de los 4 trimestres y no arrastra el error de redondeo del float.
    from app.services.reports.fiscal import _round2, vat_breakdown_by_rate

    # Mismo criterio que el 303: intracomunitarias e ISP autoliquidan
    # (devengado + deducible); el resto de recibidas es deducible interior.
    intra = [r for r in received if getattr(r, "fiscal_regime", None) == "intracomunitario"]
    isp = [r for r in received if getattr(r, "fiscal_regime", None) == "isp"]
    general_received = [r for r in received if getattr(r, "fiscal_regime", None) not in ("intracomunitario", "isp")]

    devengado = vat_breakdown_by_rate(issued)
    deducible = vat_breakdown_by_rate(general_received + isp)
    intra_bd = vat_breakdown_by_rate(intra)
    isp_bd = vat_breakdown_by_rate(isp)

    def _rows(m: dict) -> list[dict]:
        return sorted(
            (
                {"rate": float(rate), "base": float(_round2(v["base"])), "quota": float(_round2(v["quota"]))}
                for rate, v in m.items()
            ),
            key=lambda x: x["rate"],
        )

    cuota_intra = sum((v["quota"] for v in intra_bd.values()), Decimal("0"))
    cuota_isp = sum((v["quota"] for v in isp_bd.values()), Decimal("0"))

    total_devengado = _round2(sum((v["quota"] for v in devengado.values()), Decimal("0")) + cuota_intra + cuota_isp)
    total_deducible = _round2(sum((v["quota"] for v in deducible.values()), Decimal("0")) + cuota_intra)
    resultado = _round2(total_devengado - total_deducible)

    return {
        "modelo": "390",
        "ejercicio": year,
        "tenant": {"name": tenant_name, "nif": tenant_nif},
        "iva_devengado": _rows(devengado),
        "iva_deducible": _rows(deducible),
        "iva_intracomunitario": _rows(intra_bd),
        "iva_isp": _rows(isp_bd),
        "total_devengado": float(total_devengado),
        "total_deducible": float(total_deducible),
        "resultado_anual": float(resultado),
        "num_facturas_emitidas": len(issued),
        "num_facturas_recibidas": len(received),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Modelo 115 — Retenciones IRPF de arrendamientos urbanos (trimestral)
# ─────────────────────────────────────────────────────────────────────────────

# Tipo de retención vigente (19% desde 2016). Confirmar anualmente.
TIPO_RETENCION_115 = Decimal("19.0")

# Palabras clave para detectar alquileres en facturas recibidas. Heurístico —
# se afinará cuando exista campo `category` o flag explícito en Invoice.
_KEYWORDS_ALQUILER = (
    "alquiler",
    "arrendamiento",
    "renta inmueble",
    "renta local",
    "renta oficina",
    "renta nave",
    "lease",
    "leasing inmobiliario",
)


def _is_alquiler(text: str | None) -> bool:
    if not text:
        return False
    low = text.lower()
    return any(kw in low for kw in _KEYWORDS_ALQUILER)


async def build_modelo_115_data(
    db: AsyncSession,
    tenant_id: UUID,
    quarter: int,
    year: int,
) -> dict[str, Any]:
    """Modelo 115 — retenciones e ingresos a cuenta de rendimientos del capital
    inmobiliario (alquileres de inmuebles urbanos).

    Heurístico v1: detecta facturas RECIBIDAS cuya descripción o notas
    contengan palabras clave de arrendamiento ("alquiler", "arrendamiento"…).
    Para cada una calcula 19% sobre la base imponible.

    LIMITACIÓN: la app no tiene un flag "tipo: alquiler" en facturas, así que
    la detección puede dar falsos negativos si el proveedor no escribe la
    palabra clave en el concepto. Recomendado validar la lista antes de
    presentar.
    """
    if quarter not in (1, 2, 3, 4):
        raise ValueError("quarter debe ser 1, 2, 3 o 4")

    quarter_months = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
    m_start, m_end = quarter_months[quarter]
    start = date(year, m_start, 1)
    end = date(year, m_end, monthrange(year, m_end)[1])

    tenant_name, tenant_nif = await _get_tenant_info(db, tenant_id)

    facturas = await _invoices_in_period(
        db,
        tenant_id,
        invoice_type="received",
        start=start,
        end=end,
    )

    # Cargar clientes (=proveedores en facturas recibidas) para enriquecer
    proveedor_ids = {f.client_id for f in facturas if f.client_id}
    proveedores_by_id: dict[Any, Client] = {}
    if proveedor_ids:
        pq = await db.execute(select(Client).where(Client.id.in_(proveedor_ids)))
        proveedores_by_id = {c.id: c for c in pq.scalars().all()}

    arrendadores: list[dict[str, Any]] = []
    total_base = Decimal("0")
    total_retencion = Decimal("0")

    for inv in facturas:
        # Buscar en notes, terms y en cualquier descripción de línea
        texto = " ".join(
            filter(
                None,
                [
                    inv.notes,
                    inv.terms,
                    *[ln.description for ln in (inv.lines or [])],
                ],
            )
        )
        if not _is_alquiler(texto):
            continue

        base = Decimal(str(inv.amount_base or 0))
        retencion = (base * TIPO_RETENCION_115 / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        prov = proveedores_by_id.get(inv.client_id)
        arrendadores.append(
            {
                "invoice_id": str(inv.id),
                "invoice_number": inv.invoice_number,
                "nif_arrendador": (prov.nif if prov else None) or "",
                "nombre_arrendador": (prov.name if prov else None) or "",
                "fecha": inv.date.date().isoformat() if hasattr(inv.date, "date") else str(inv.date)[:10],
                "concepto": (inv.notes or (inv.lines[0].description if inv.lines else "") or "")[:160],
                "base_retencion": float(base),
                "retencion_practicada": float(retencion),
            }
        )
        total_base += base
        total_retencion += retencion

    arrendadores.sort(key=lambda x: (x["nif_arrendador"], x["fecha"]))

    return {
        "modelo": "115",
        "ejercicio": year,
        "periodo": f"{quarter}T",
        "tenant": {"name": tenant_name, "nif": tenant_nif},
        "tipo_retencion_pct": float(TIPO_RETENCION_115),
        "arrendadores": arrendadores,
        "num_arrendadores": len({a["nif_arrendador"] for a in arrendadores if a["nif_arrendador"]}),
        "num_facturas": len(arrendadores),
        "total_base_retenciones": float(total_base),
        "total_retencion_practicada": float(total_retencion),
        "deteccion": "heuristico_keywords",
        "_warning": (
            "Detección heurística por palabras clave en concepto/notas. "
            "Revisa la lista antes de presentar; pueden faltar alquileres si el proveedor "
            "no usa términos como 'alquiler' o 'arrendamiento' en la factura."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Modelo 349 — Operaciones intracomunitarias (trimestral)
# ─────────────────────────────────────────────────────────────────────────────

# Prefijos de país UE para detectar NIF intracomunitarios.
# ES queda excluido (es operación interior, no entra en el 349).
_UE_PREFIXES = {
    "AT",
    "BE",
    "BG",
    "HR",
    "CY",
    "CZ",
    "DK",
    "EE",
    "FI",
    "FR",
    "DE",
    "EL",
    "GR",
    "HU",
    "IE",
    "IT",
    "LV",
    "LT",
    "LU",
    "MT",
    "NL",
    "PL",
    "PT",
    "RO",
    "SK",
    "SI",
    "SE",
}


def _detect_pais_ue(nif: str | None) -> str | None:
    """Devuelve el código de país UE si el NIF empieza por uno conocido."""
    if not nif:
        return None
    n = nif.strip().upper()
    if len(n) < 3:
        return None
    prefix = n[:2]
    return prefix if prefix in _UE_PREFIXES else None


async def build_modelo_349_data(
    db: AsyncSession,
    tenant_id: UUID,
    quarter: int,
    year: int,
) -> dict[str, Any]:
    """Modelo 349 — declaración recapitulativa de operaciones intracomunitarias.

    Detecta facturas EMITIDAS y RECIBIDAS cuyo cliente/proveedor tenga un NIF
    que empiece por un prefijo de país UE distinto de ES. Agrupa por
    contraparte y tipo de operación:
      - E (Entrega de bienes) → facturas emitidas
      - A (Adquisición de bienes) → facturas recibidas

    LIMITACIÓN: la app no distingue bienes vs servicios. Asumimos bienes (E/A).
    Para servicios (S/I/T) habría que añadir un campo de naturaleza a las
    líneas de factura. Documentado como mejora futura.
    """
    if quarter not in (1, 2, 3, 4):
        raise ValueError("quarter debe ser 1, 2, 3 o 4")

    quarter_months = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
    m_start, m_end = quarter_months[quarter]
    start = date(year, m_start, 1)
    end = date(year, m_end, monthrange(year, m_end)[1])

    tenant_name, tenant_nif = await _get_tenant_info(db, tenant_id)

    emitidas = await _invoices_in_period(
        db,
        tenant_id,
        invoice_type="issued",
        start=start,
        end=end,
    )
    recibidas = await _invoices_in_period(
        db,
        tenant_id,
        invoice_type="received",
        start=start,
        end=end,
    )

    todos_cli_ids = {f.client_id for f in emitidas + recibidas if f.client_id}
    cli_by_id: dict[Any, Client] = {}
    if todos_cli_ids:
        cq = await db.execute(select(Client).where(Client.id.in_(todos_cli_ids)))
        cli_by_id = {c.id: c for c in cq.scalars().all()}

    # Agrupar por (nif, tipo_operacion)
    by_key: dict[tuple[str, str], dict[str, Any]] = {}

    def _add(inv: Invoice, tipo: str) -> None:
        cli = cli_by_id.get(inv.client_id)
        nif = (cli.nif if cli else None) or ""
        pais = _detect_pais_ue(nif)
        if not pais:
            return
        key = (nif, tipo)
        entry = by_key.setdefault(
            key,
            {
                "nif_intracomunitario": nif,
                "pais_codigo": pais,
                "nombre_contraparte": (cli.name if cli else None) or "",
                "tipo_operacion": tipo,
                "base_imponible": Decimal("0"),
                "num_operaciones": 0,
            },
        )
        entry["base_imponible"] += Decimal(str(inv.amount_base or 0))
        entry["num_operaciones"] += 1

    for f in emitidas:
        _add(f, "E")
    for f in recibidas:
        _add(f, "A")

    operaciones = [
        {
            **v,
            "base_imponible": float(v["base_imponible"]),
        }
        for v in by_key.values()
    ]
    operaciones.sort(key=lambda x: (x["pais_codigo"], x["tipo_operacion"], x["nif_intracomunitario"]))

    total = sum(Decimal(str(op["base_imponible"])) for op in operaciones)

    return {
        "modelo": "349",
        "ejercicio": year,
        "periodo": f"{quarter}T",
        "tenant": {"name": tenant_name, "nif": tenant_nif},
        "operaciones": operaciones,
        "num_operadores": len({op["nif_intracomunitario"] for op in operaciones}),
        "num_lineas": len(operaciones),
        "total_base_imponible": float(total),
        "deteccion": "prefijo_nif_pais_ue",
        "_warning": (
            "Detección por prefijo de NIF (DE, FR, IT…). Solo entrega/adquisición "
            "de bienes (E/A) — los servicios intracomunitarios (S/I/T) requieren "
            "campo adicional en líneas de factura."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Modelo 100 — IRPF (Declaración de la Renta) — preview anual (F2.8)
# ─────────────────────────────────────────────────────────────────────────────

# Escala general del IRPF (estatal + autonómica, tipo medio orientativo
# 2024/2025). La parte autonómica varía por comunidad — esto es un PREVIEW.
_IRPF_BRACKETS: list[tuple[Decimal | None, Decimal]] = [
    (Decimal("12450"), Decimal("19")),
    (Decimal("20200"), Decimal("24")),
    (Decimal("35200"), Decimal("30")),
    (Decimal("60000"), Decimal("37")),
    (Decimal("300000"), Decimal("45")),
    (None, Decimal("47")),
]
MINIMO_PERSONAL_DEFAULT = Decimal("5550")


def _irpf_cuota(base: Decimal) -> Decimal:
    """Cuota IRPF aplicando la escala progresiva por tramos sobre la base."""
    if base <= 0:
        return Decimal("0.00")
    cuota = Decimal("0")
    prev = Decimal("0")
    for limite, tipo in _IRPF_BRACKETS:
        top = base if limite is None else min(base, limite)
        if top > prev:
            cuota += (top - prev) * tipo / Decimal("100")
            prev = top
        if limite is None or base <= limite:
            break
    return cuota.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def build_modelo_100_data(
    db: AsyncSession,
    tenant_id: UUID,
    year: int,
    *,
    minimo_personal: Decimal | float | None = None,
    pagos_fraccionados_pagados: Decimal | float = 0,
) -> dict[str, Any]:
    """Preview del Modelo 100 (IRPF — Renta) para autónomos en estimación directa.

    **MVP / preview**. La Renta real integra rendimientos del trabajo, capital
    mobiliario/inmobiliario, ganancias/pérdidas patrimoniales, mínimos personales
    y familiares completos y deducciones autonómicas que no están en el ERP.
    Aquí estimamos solo el rendimiento de actividad económica:

        Ingresos (facturas emitidas)
      - Gastos (facturas recibidas + coste de personal)
      = Rendimiento neto de la actividad
      - mínimo personal y familiar (5.550€ por defecto)
      = Base liquidable
      × escala IRPF progresiva
      = Cuota íntegra
      - retenciones soportadas (IRPF retenido en facturas emitidas)
      - pagos fraccionados (Modelo 130 ya presentados)
      = Resultado de la declaración
    """
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    tenant_name, tenant_nif = await _get_tenant_info(db, tenant_id)

    issued = await _invoices_in_period(db, tenant_id, invoice_type="issued", start=start, end=end)
    received = await _invoices_in_period(db, tenant_id, invoice_type="received", start=start, end=end)
    payrolls = await _payrolls_in_period(db, tenant_id, start=start, end=end)

    ingresos = sum((Decimal(i.amount_base or 0) for i in issued), Decimal(0))
    gastos_facturas = sum((Decimal(i.amount_base or 0) for i in received), Decimal(0))

    coste_nominas = Decimal(0)
    for p in payrolls:
        bruto = Decimal(p.gross_salary or p.base_salary or 0)
        cuotas = p.cuotas_empresa_json or {}
        if isinstance(cuotas, dict) and cuotas:
            ss_empresa = sum(Decimal(str(v or 0)) for v in cuotas.values())
        else:
            ss_empresa = bruto * Decimal("0.30")
        coste_nominas += bruto + ss_empresa

    rendimiento_neto = ingresos - gastos_facturas - coste_nominas
    minp = Decimal(str(minimo_personal)) if minimo_personal is not None else MINIMO_PERSONAL_DEFAULT
    base_liquidable = max(Decimal(0), rendimiento_neto - minp)
    cuota_integra = _irpf_cuota(base_liquidable)

    retenciones = sum((Decimal(i.retencion_irpf_amount or 0) for i in issued), Decimal(0))
    pagos = Decimal(str(pagos_fraccionados_pagados or 0))
    resultado = cuota_integra - retenciones - pagos

    return {
        "modelo": "100",
        "ejercicio": year,
        "tenant": {"name": tenant_name, "nif": tenant_nif},
        "ingresos": float(ingresos),
        "gastos_facturas": float(gastos_facturas),
        "coste_nominas": float(round(coste_nominas, 2)),
        "rendimiento_neto": float(round(rendimiento_neto, 2)),
        "minimo_personal": float(minp),
        "base_liquidable": float(round(base_liquidable, 2)),
        "cuota_integra": float(cuota_integra),
        "retenciones_soportadas": float(round(retenciones, 2)),
        "pagos_fraccionados_pagados": float(pagos),
        "resultado_declaracion": float(round(resultado, 2)),
        "signo": ("ingresar" if resultado > 0 else "devolver" if resultado < 0 else "cero"),
        "_warning": (
            "Preview no oficial. La Declaración de la Renta (Modelo 100) real "
            "incluye rendimientos del trabajo, del capital, ganancias/pérdidas "
            "patrimoniales, mínimos familiares y deducciones autonómicas que no "
            "están en el ERP. Esta estimación cubre solo el rendimiento de "
            "actividad económica. Revísala con tu asesor antes de presentar."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Modelo 200 — Impuesto sobre Sociedades (F2.8)
# ─────────────────────────────────────────────────────────────────────────────

# Tipo general del Impuesto sobre Sociedades en España.
# (RD-Ley 4/2013 + Ley 27/2014). Algunos casos especiales:
#   - 23% para entidades de reducida dimensión (cifra negocio < 1M€) — desde 2023.
#   - 15% durante 2 ejercicios para entidades de nueva creación.
# El cálculo abajo expone los tipos disponibles y el usuario puede sobreescribir
# `tipo_impositivo_pct` cuando llame al endpoint.
TIPO_IS_GENERAL = Decimal("25")
TIPO_IS_REDUCIDO = Decimal("23")  # ERD < 1M cifra negocio
TIPO_IS_NUEVA_CREACION = Decimal("15")
UMBRAL_ERD = Decimal("1000000")  # 1M€ — frontera ERD


async def build_modelo_200_data(
    db: AsyncSession,
    tenant_id: UUID,
    year: int,
    *,
    tipo_impositivo_pct: Decimal | float | None = None,
    pagos_fraccionados_pagados: Decimal | float = 0,
) -> dict[str, Any]:
    """Agrega datos para el Modelo 200 — Impuesto sobre Sociedades.

    **MVP**. El cálculo oficial del 200 incluye ajustes fiscales (provisiones,
    deterioros, amortizaciones aceleradas, compensación de BINs, deducciones
    por I+D+i, etc.) que requieren información no estructurada en el ERP.
    Esta función calcula un PREVIEW útil para que la pyme estime la cuota:

        Ingresos del ejercicio (facturas emitidas)
      - Gastos del ejercicio (facturas recibidas + coste empresa nóminas)
      = Resultado contable preliminar
      ─ ajustes fiscales (0 por defecto, declarables por el usuario en el frontend)
      = Base imponible
      × tipo impositivo
      = Cuota íntegra
      - retenciones soportadas
      - pagos fraccionados (Modelo 202 ya presentados)
      = Resultado de la declaración

    Si la cifra de negocio del año es < 1M€ y no se ha indicado tipo, se
    aplica el tipo reducido del 23% por defecto.
    """
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    tenant_name, tenant_nif = await _get_tenant_info(db, tenant_id)

    issued = await _invoices_in_period(db, tenant_id, invoice_type="issued", start=start, end=end)
    received = await _invoices_in_period(db, tenant_id, invoice_type="received", start=start, end=end)
    payrolls = await _payrolls_in_period(db, tenant_id, start=start, end=end)

    cifra_negocio = sum((Decimal(i.amount_base or 0) for i in issued), Decimal(0))
    gastos_facturas = sum((Decimal(i.amount_base or 0) for i in received), Decimal(0))

    # Coste empresa de nómina ≈ bruto + cuotas empresa (SS empresarial). Si
    # cuotas_empresa_json no está, asumimos 30% del bruto como estimación.
    coste_nominas = Decimal(0)
    for p in payrolls:
        bruto = Decimal(p.gross_salary or p.base_salary or 0)
        cuotas = p.cuotas_empresa_json or {}
        if isinstance(cuotas, dict) and cuotas:
            ss_empresa = sum(Decimal(str(v or 0)) for v in cuotas.values())
        else:
            ss_empresa = bruto * Decimal("0.30")
        coste_nominas += bruto + ss_empresa

    resultado_contable = cifra_negocio - gastos_facturas - coste_nominas

    if tipo_impositivo_pct is None:
        tipo = TIPO_IS_REDUCIDO if cifra_negocio < UMBRAL_ERD else TIPO_IS_GENERAL
    else:
        tipo = Decimal(str(tipo_impositivo_pct))

    base_imponible = resultado_contable  # ajustes fiscales = 0 en MVP
    cuota_integra = max(Decimal(0), base_imponible * tipo / Decimal(100))

    retenciones = sum((Decimal(i.retencion_irpf_amount or 0) for i in issued), Decimal(0))
    pagos = Decimal(str(pagos_fraccionados_pagados or 0))
    resultado_declaracion = cuota_integra - retenciones - pagos

    return {
        "modelo": "200",
        "ejercicio": year,
        "tenant": {"name": tenant_name, "nif": tenant_nif},
        "cifra_negocio": float(cifra_negocio),
        "gastos_facturas": float(gastos_facturas),
        "coste_nominas": float(coste_nominas),
        "resultado_contable": float(round(resultado_contable, 2)),
        "ajustes_fiscales": 0.0,
        "base_imponible": float(round(base_imponible, 2)),
        "tipo_impositivo_pct": float(tipo),
        "cuota_integra": float(round(cuota_integra, 2)),
        "retenciones_soportadas": float(round(retenciones, 2)),
        "pagos_fraccionados_pagados": float(pagos),
        "resultado_declaracion": float(round(resultado_declaracion, 2)),
        "signo": ("ingresar" if resultado_declaracion > 0 else "devolver" if resultado_declaracion < 0 else "cero"),
        "_warning": (
            "Preview no oficial. El Modelo 200 real exige ajustes fiscales "
            "(provisiones, amortizaciones aceleradas, compensación BINs, "
            "deducciones I+D+i…) que deben revisarse con asesor antes de presentar."
        ),
    }
