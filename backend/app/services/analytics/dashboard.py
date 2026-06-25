"""Dashboard analytics aggregation.

Single source of truth for the /analytics/dashboard endpoint.
Returns a complete snapshot for a given period (YYYY-MM): facturas, banca,
RRHH, IA tasks, top clientes, cashflow histórico (6 meses) y estado de
facturas. Demo bank transactions (description prefijada con [DEMO])
quedan excluidas para no contaminar las métricas.

Estados de Invoice válidos según state_machine: draft, pending, sent, paid, cancelled.
"""

from __future__ import annotations

import uuid
from calendar import monthrange
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import case, desc, extract, func, not_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.billing import InvoiceLine
from app.db.models.hr import Expense, JornadaRecord, LeaveRequest
from app.db.models.inventory import Product, StockMovement
from app.db.models.models import (
    BankTransaction,
    Client,
    Employee,
    Invoice,
    Payroll,
    Task,
)
from app.db.models.tasks import AgentExecutionTrace
from app.services.cache import cached_json

# TTL del dashboard: 5 min. Valor de compromiso entre frescura percibida
# (si el usuario crea una factura quiere verla) y coste (11 agregaciones
# pesadas por cada miss). Para invalidación inmediata tras mutaciones
# significativas, el endpoint de mutación puede llamar cache_invalidate.
_DASHBOARD_TTL_SECONDS = 300

DEMO_TX_PREFIX = "[DEMO]"
# Facturas EMITIDAS por nosotros = issued + rectificativas/abono (mismo conjunto
# canónico que services/billing/commands.py y el índice único parcial). Las
# rectificativas llevan amount_total negativo, así que func.sum() las neutraliza
# correctamente en ingresos/IVA/top-clientes; excluirlas sobreestimaba las cifras (B8).
_EMITTED = ("issued", "rectificativa")
_MONTHS_ES = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
]
_MONTHS_ES_FULL = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


def iter_months_back(end_month: date, n: int) -> list[tuple[date, date, str]]:
    """Devuelve [(start, end, label_corto)] para los n meses que terminan en end_month, más antiguo primero.

    Aritmética de meses real (no aproximación con días) — evita el bug de
    saltarse meses al usar timedelta(days=28*i).
    """
    result: list[tuple[date, date, str]] = []
    y, m = end_month.year, end_month.month
    for _ in range(n):
        last_day = monthrange(y, m)[1]
        result.append((date(y, m, 1), date(y, m, last_day), _MONTHS_ES[m - 1]))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(result))


def _period_label(start: date) -> str:
    return f"{_MONTHS_ES_FULL[start.month - 1]} {start.year}"


def _real_tx_filter():
    """Filtro SQLAlchemy para excluir transacciones marcadas como demo."""
    return not_(BankTransaction.description.like(f"{DEMO_TX_PREFIX}%"))


def _dashboard_cache_key(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    period: str,
    start: date,
    end: date,
) -> str:
    return f"dashboard:v4:{tenant_id}:{period}:{start}:{end}"


async def latest_period_with_data(db: AsyncSession, tenant_id: uuid.UUID) -> str | None:
    """Último mes (YYYY-MM) con alguna factura del tenant; None si no hay ninguna.

    Permite que el dashboard abra por defecto en el mes con actividad más reciente
    en vez del mes natural en curso —que suele estar vacío a principio de mes y
    hace parecer que 'no hay datos' aunque sí los haya en meses anteriores.
    """
    res = await db.execute(select(func.max(Invoice.date)).where(Invoice.tenant_id == tenant_id))
    dt = res.scalar()
    return dt.strftime("%Y-%m") if dt else None


@cached_json(key=_dashboard_cache_key, ttl_seconds=_DASHBOARD_TTL_SECONDS)
async def get_dashboard(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    period: str,
    start: date,
    end: date,
) -> dict:
    """Agrega todas las métricas del dashboard para un periodo (YYYY-MM).

    Cacheado en Redis con TTL de 5 min (ver `_DASHBOARD_TTL_SECONDS`).
    Si Redis no está disponible (sin REDIS_URL), se ejecuta sin caché.
    """
    today = date.today()

    # ── Facturas: agregaciones del periodo ───────────────────────────────
    issued_period_q = select(
        func.coalesce(func.sum(Invoice.amount_total), 0),
        func.count(),
        # Issued-only (excluye rectificativas/abono): para el ticket medio, que
        # debe medir la media de facturas EMITIDAS reales. Una rectificativa lleva
        # amount_total negativo y restaría del numerador a la vez que suma +1 al
        # denominador, infravalorando el ticket. Ver ticket_medio_periodo abajo.
        func.coalesce(
            func.sum(case((Invoice.invoice_type == "issued", Invoice.amount_total), else_=0)),
            0,
        ),
        func.coalesce(
            func.sum(case((Invoice.invoice_type == "issued", 1), else_=0)),
            0,
        ),
    ).where(
        Invoice.tenant_id == tenant_id,
        Invoice.invoice_type.in_(_EMITTED),
        func.date(Invoice.date) >= start,
        func.date(Invoice.date) <= end,
    )
    received_period_q = select(
        func.coalesce(func.sum(Invoice.amount_total), 0),
        func.count(),
    ).where(
        Invoice.tenant_id == tenant_id,
        Invoice.invoice_type == "received",
        func.date(Invoice.date) >= start,
        func.date(Invoice.date) <= end,
    )
    ingresos_periodo_t, emitidas_periodo, issued_sum_t, issued_count = (
        await db.execute(issued_period_q)
    ).one()
    gastos_periodo_t, recibidas_periodo = (await db.execute(received_period_q)).one()
    ingresos_periodo = float(ingresos_periodo_t or 0)
    gastos_periodo = float(gastos_periodo_t or 0)
    beneficio_periodo = ingresos_periodo - gastos_periodo
    margen_periodo_pct = (
        round((beneficio_periodo / ingresos_periodo) * 100, 1)
        if ingresos_periodo > 0
        else 0.0
    )

    # ── Facturas: agregaciones acumuladas (todo el histórico) ────────────
    status_breakdown_q = select(
        Invoice.status,
        func.count(),
        func.coalesce(func.sum(Invoice.amount_total), 0),
    ).where(
        Invoice.tenant_id == tenant_id,
        Invoice.invoice_type.in_(_EMITTED),
    ).group_by(Invoice.status)
    status_rows = (await db.execute(status_breakdown_q)).all()

    status_counts: dict[str, int] = {}
    status_amounts: dict[str, float] = {}
    for st, cnt, amt in status_rows:
        status_counts[st] = int(cnt or 0)
        status_amounts[st] = float(amt or 0)

    pagadas_count = status_counts.get("paid", 0)
    pendientes_count = status_counts.get("pending", 0) + status_counts.get("sent", 0)
    borradores_count = status_counts.get("draft", 0)
    canceladas_count = status_counts.get("cancelled", 0)

    importe_pendiente_cobro = status_amounts.get("pending", 0.0) + status_amounts.get("sent", 0.0)

    total_ingresos_q = select(func.coalesce(func.sum(Invoice.amount_total), 0)).where(
        Invoice.tenant_id == tenant_id,
        Invoice.invoice_type.in_(_EMITTED),
        Invoice.status != "cancelled",
    )
    total_gastos_q = select(func.coalesce(func.sum(Invoice.amount_total), 0)).where(
        Invoice.tenant_id == tenant_id,
        Invoice.invoice_type == "received",
        Invoice.status != "cancelled",
    )
    total_ingresos = float((await db.execute(total_ingresos_q)).scalar() or 0)
    total_gastos = float((await db.execute(total_gastos_q)).scalar() or 0)
    beneficio = total_ingresos - total_gastos
    margen_pct = round((beneficio / total_ingresos) * 100, 1) if total_ingresos > 0 else 0.0

    emitidas_count = (
        pagadas_count + pendientes_count + borradores_count + canceladas_count
    )
    received_count_q = select(func.count()).where(
        Invoice.tenant_id == tenant_id, Invoice.invoice_type == "received"
    )
    recibidas_count = int((await db.execute(received_count_q)).scalar() or 0)

    # ── Próximas a vencer (pendientes de cobro + due_date <= hoy+7) ──────
    due_soon_q = select(
        func.count(), func.coalesce(func.sum(Invoice.amount_total), 0)
    ).where(
        Invoice.tenant_id == tenant_id,
        Invoice.invoice_type.in_(_EMITTED),
        Invoice.status.in_(["pending", "sent"]),
        Invoice.due_date.is_not(None),
        Invoice.due_date <= today + timedelta(days=7),
    )
    due_soon_row = (await db.execute(due_soon_q)).one()
    vencen_proximos_count = int(due_soon_row[0] or 0)
    vencen_proximos_amount = float(due_soon_row[1] or 0)

    # ── Cashflow histórico: 6 meses terminando en el periodo seleccionado ─
    cashflow: list[dict] = []
    for m_start, m_end, label in iter_months_back(start, 6):
        ing_q = select(func.coalesce(func.sum(Invoice.amount_total), 0)).where(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_type.in_(_EMITTED),
            Invoice.status != "cancelled",
            func.date(Invoice.date) >= m_start,
            func.date(Invoice.date) <= m_end,
        )
        gas_q = select(func.coalesce(func.sum(Invoice.amount_total), 0)).where(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_type == "received",
            Invoice.status != "cancelled",
            func.date(Invoice.date) >= m_start,
            func.date(Invoice.date) <= m_end,
        )
        ing = float((await db.execute(ing_q)).scalar() or 0)
        gas = float((await db.execute(gas_q)).scalar() or 0)
        cashflow.append({
            "month": label,
            "ingresos": round(ing, 2),
            "gastos": round(gas, 2),
            "beneficio": round(ing - gas, 2),
        })

    # ── Top clientes del periodo ─────────────────────────────────────────
    top_q = (
        select(Client.name, func.coalesce(func.sum(Invoice.amount_total), 0).label("total"))
        .join(Invoice, Invoice.client_id == Client.id)
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_type.in_(_EMITTED),
            Invoice.status != "cancelled",
            func.date(Invoice.date) >= start,
            func.date(Invoice.date) <= end,
        )
        .group_by(Client.name)
        .order_by(desc("total"))
        .limit(5)
    )
    top_clientes = [
        {"name": name or "Desconocido", "total": float(total)}
        for name, total in (await db.execute(top_q)).all()
    ]

    # ── Estado de facturas (para pie chart, sólo emitidas con importe) ───
    estado_facturas = []
    for label, keys in (
        ("Cobradas", ("paid",)),
        ("Pendientes", ("pending", "sent")),
        ("Borradores", ("draft",)),
        ("Canceladas", ("cancelled",)),
    ):
        val = sum(status_amounts.get(k, 0.0) for k in keys)
        if val > 0:
            estado_facturas.append({"name": label, "value": round(val, 2)})

    # ── RRHH ─────────────────────────────────────────────────────────────
    emp_q = select(func.count()).where(
        Employee.tenant_id == tenant_id, Employee.status == "active"
    )
    empleados_activos = int((await db.execute(emp_q)).scalar() or 0)

    payroll_periodo_q = select(
        func.coalesce(func.sum(Payroll.net_salary), 0),
        func.count(),
        func.count().filter(Payroll.status == "paid"),
    ).where(
        Payroll.tenant_id == tenant_id,
        Payroll.period_start >= start,
        Payroll.period_end <= end,
    )
    pay_sum, pay_total, pay_paid = (await db.execute(payroll_periodo_q)).one()
    coste_nominas = float(pay_sum)
    nominas_pagadas = int(pay_paid)
    nominas_pendientes = int(pay_total) - nominas_pagadas

    # ── Banca (excluyendo demo) ──────────────────────────────────────────
    bank_period_q = select(
        func.coalesce(func.sum(BankTransaction.amount).filter(BankTransaction.amount > 0), 0),
        func.coalesce(func.sum(BankTransaction.amount).filter(BankTransaction.amount < 0), 0),
        func.count(),
        func.count().filter(BankTransaction.status == "reconciled"),
    ).where(
        BankTransaction.tenant_id == tenant_id,
        BankTransaction.date >= start,
        BankTransaction.date <= end,
        _real_tx_filter(),
    )
    tx_in, tx_out, tx_total, tx_reconciled = (await db.execute(bank_period_q)).one()
    entradas_periodo = float(tx_in)
    salidas_periodo = abs(float(tx_out))
    transacciones_periodo = int(tx_total)
    reconciliadas = int(tx_reconciled)
    pendientes_conciliar = transacciones_periodo - reconciliadas

    # Saldo actual = balance de la transacción real más reciente
    last_tx_q = (
        select(BankTransaction.balance)
        .where(BankTransaction.tenant_id == tenant_id, _real_tx_filter())
        .order_by(desc(BankTransaction.date), desc(BankTransaction.created_at))
        .limit(1)
    )
    last_balance = (await db.execute(last_tx_q)).scalar()
    saldo_actual = float(last_balance) if last_balance is not None else 0.0

    # ¿Hay datos demo en el tenant?
    has_demo_q = select(func.count()).where(
        BankTransaction.tenant_id == tenant_id,
        BankTransaction.description.like(f"{DEMO_TX_PREFIX}%"),
    )
    has_demo_data = int((await db.execute(has_demo_q)).scalar() or 0) > 0

    # ── IA / Tasks ───────────────────────────────────────────────────────
    tasks_total_q = select(Task.status, func.count()).where(
        Task.tenant_id == tenant_id
    ).group_by(Task.status)
    tasks_rows = (await db.execute(tasks_total_q)).all()
    tasks_by_status: dict[str, int] = {st: int(c) for st, c in tasks_rows}
    tasks_done = tasks_by_status.get("done", 0)
    tasks_failed = tasks_by_status.get("failed", 0)
    tasks_pending = (
        tasks_by_status.get("pending", 0)
        + tasks_by_status.get("planning", 0)
        + tasks_by_status.get("executing", 0)
        + tasks_by_status.get("awaiting_approval", 0)
    )
    tasks_total = sum(tasks_by_status.values())
    tasks_terminadas = tasks_done + tasks_failed
    tasks_success_rate = (
        round((tasks_done / tasks_terminadas) * 100) if tasks_terminadas > 0 else 0
    )

    tasks_periodo_q = select(func.count()).where(
        Task.tenant_id == tenant_id,
        Task.created_at >= datetime.combine(start, datetime.min.time()),
        Task.created_at <= datetime.combine(end, datetime.max.time()),
    )
    tasks_periodo = int((await db.execute(tasks_periodo_q)).scalar() or 0)

    # ── Clientes totales y nuevos del periodo ────────────────────────────
    total_clients_q = select(func.count()).where(Client.tenant_id == tenant_id)
    total_clientes = int((await db.execute(total_clients_q)).scalar() or 0)
    new_clients_q = select(func.count()).where(
        Client.tenant_id == tenant_id,
        func.date(Client.created_at) >= start,
        func.date(Client.created_at) <= end,
    )
    nuevos_clientes_periodo = int((await db.execute(new_clients_q)).scalar() or 0)

    # ── Ventas: ticket medio, IVA, top productos, día de la semana ──────
    # Ticket medio = media de facturas EMITIDAS reales (issued-only). Excluye
    # rectificativas tanto del numerador como del denominador: un abono negativo
    # no es una "venta" y contarlo infravaloraba el ticket (5 fras de 1000€ + 1
    # rectificativa -200€ daba 4800/6=800€ en vez de 5000/5=1000€).
    ticket_medio_periodo = (
        round(float(issued_sum_t or 0) / int(issued_count or 0), 2)
        if int(issued_count or 0) > 0
        else 0.0
    )

    # IVA breakdown: agrupado por tax_percentage (sólo facturas emitidas del periodo)
    # coalesce sobre discount_percentage por seguridad si llega NULL en datos antiguos.
    iva_rate_expr = func.coalesce(InvoiceLine.tax_percentage, 0)
    iva_q = (
        select(
            iva_rate_expr.label("rate"),
            func.coalesce(
                func.sum(
                    InvoiceLine.quantity
                    * InvoiceLine.unit_price
                    * (1 - func.coalesce(InvoiceLine.discount_percentage, 0) / 100)
                ),
                0,
            ).label("base"),
            func.coalesce(func.sum(InvoiceLine.total), 0).label("total_con_iva"),
        )
        .join(Invoice, Invoice.id == InvoiceLine.invoice_id)
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_type.in_(_EMITTED),
            Invoice.status != "cancelled",
            func.date(Invoice.date) >= start,
            func.date(Invoice.date) <= end,
        )
        .group_by(iva_rate_expr)
        .order_by(desc("total_con_iva"))
    )
    iva_breakdown = [
        {
            "rate": float(rate or 0),
            "base": round(float(base or 0), 2),
            "iva": round(float(total or 0) - float(base or 0), 2),
            "total": round(float(total or 0), 2),
        }
        for rate, base, total in (await db.execute(iva_q)).all()
    ]

    # Top productos del periodo. Usa Product.name si la línea tiene product_id,
    # si no cae al description (líneas libres). Así contamos también facturación
    # de servicios/items sin catalogar.
    # Importante: GROUP BY usa la expresión completa, no el alias.
    # PostgreSQL rechaza `GROUP BY <alias>` cuando el alias envuelve columnas
    # no agregadas con COALESCE; exige las columnas en el GROUP BY explícito.
    product_name = func.coalesce(Product.name, InvoiceLine.description, "Sin nombre")
    top_prod_q = (
        select(
            product_name.label("name"),
            func.coalesce(func.sum(InvoiceLine.quantity), 0).label("cantidad"),
            func.coalesce(func.sum(InvoiceLine.total), 0).label("total"),
        )
        .select_from(InvoiceLine)
        .join(Invoice, Invoice.id == InvoiceLine.invoice_id)
        .outerjoin(Product, Product.id == InvoiceLine.product_id)
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_type.in_(_EMITTED),
            Invoice.status != "cancelled",
            func.date(Invoice.date) >= start,
            func.date(Invoice.date) <= end,
        )
        .group_by(product_name)
        .order_by(desc("total"))
        .limit(5)
    )
    top_productos = [
        {
            "name": name or "Sin nombre",
            "cantidad": float(cant or 0),
            "total": round(float(tot or 0), 2),
        }
        for name, cant, tot in (await db.execute(top_prod_q)).all()
    ]

    # Facturación por día de la semana (1=Lunes … 7=Domingo en isodow Postgres)
    dow_expr = extract("isodow", Invoice.date)
    dow_q = (
        select(
            dow_expr.label("dow"),
            func.coalesce(func.sum(Invoice.amount_total), 0).label("total"),
            func.count().label("n"),
        )
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_type.in_(_EMITTED),
            Invoice.status != "cancelled",
            func.date(Invoice.date) >= start,
            func.date(Invoice.date) <= end,
        )
        .group_by(dow_expr)
        .order_by(dow_expr)
    )
    _DOW_LABELS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    dow_rows = {int(r[0]): (float(r[1] or 0), int(r[2] or 0)) for r in (await db.execute(dow_q)).all()}
    por_dia_semana = [
        {
            "dia": _DOW_LABELS[i],
            "ingresos": round(dow_rows.get(i + 1, (0.0, 0))[0], 2),
            "n": dow_rows.get(i + 1, (0.0, 0))[1],
        }
        for i in range(7)
    ]

    # ── Aging cobros / pagos (facturas con due_date vencido o por vencer) ─
    def _aging_query(tipo: str):
        bucket_expr = case(
            (func.date(Invoice.due_date) - today <= -90, "vencido_90"),
            (func.date(Invoice.due_date) - today <= -60, "vencido_60_90"),
            (func.date(Invoice.due_date) - today <= -30, "vencido_30_60"),
            (func.date(Invoice.due_date) - today <= 0, "vencido_0_30"),
            (func.date(Invoice.due_date) - today <= 30, "vence_0_30"),
            else_="vence_30plus",
        )
        return (
            select(
                bucket_expr.label("bucket"),
                func.count().label("n"),
                func.coalesce(func.sum(Invoice.amount_total), 0).label("importe"),
            )
            .where(
                Invoice.tenant_id == tenant_id,
                Invoice.invoice_type == tipo,
                Invoice.status.in_(["pending", "sent"]),
                Invoice.due_date.is_not(None),
            )
            .group_by(bucket_expr)
        )

    _BUCKETS = ["vencido_90", "vencido_60_90", "vencido_30_60", "vencido_0_30", "vence_0_30", "vence_30plus"]
    aging_cobros = {b: {"n": 0, "importe": 0.0} for b in _BUCKETS}
    for b, n, imp in (await db.execute(_aging_query("issued"))).all():
        if b in aging_cobros:
            aging_cobros[b] = {"n": int(n or 0), "importe": round(float(imp or 0), 2)}

    aging_pagos = {b: {"n": 0, "importe": 0.0} for b in _BUCKETS}
    for b, n, imp in (await db.execute(_aging_query("received"))).all():
        if b in aging_pagos:
            aging_pagos[b] = {"n": int(n or 0), "importe": round(float(imp or 0), 2)}

    # ── DSO / DPO (días) ─────────────────────────────────────────────────
    dias_periodo = (end - start).days + 1
    importe_pendiente_pago = sum(v["importe"] for v in aging_pagos.values())
    dso_dias = (
        round((importe_pendiente_cobro / ingresos_periodo) * dias_periodo, 1)
        if ingresos_periodo > 0 else 0.0
    )
    dpo_dias = (
        round((importe_pendiente_pago / gastos_periodo) * dias_periodo, 1)
        if gastos_periodo > 0 else 0.0
    )

    # ── RRHH detalle ─────────────────────────────────────────────────────
    coste_medio_empleado = (
        round(coste_nominas / empleados_activos, 2) if empleados_activos > 0 else 0.0
    )

    dept_q = (
        select(
            func.coalesce(Employee.department, "Sin departamento").label("dept"),
            func.count().label("n"),
            func.coalesce(func.sum(Employee.base_salary), 0).label("salarios"),
        )
        .where(Employee.tenant_id == tenant_id, Employee.status == "active")
        .group_by("dept")
        .order_by(desc("n"))
    )
    rrhh_por_departamento = [
        {"departamento": d, "empleados": int(n or 0), "coste_base": round(float(s or 0), 2)}
        for d, n, s in (await db.execute(dept_q)).all()
    ]

    # Horas ordinarias / extra del periodo
    horas_q = select(
        func.coalesce(func.sum(JornadaRecord.horas_ordinarias), 0),
        func.coalesce(func.sum(JornadaRecord.horas_extra), 0),
    ).where(
        JornadaRecord.tenant_id == tenant_id,
        JornadaRecord.fecha >= start,
        JornadaRecord.fecha <= end,
    )
    horas_ord_t, horas_ext_t = (await db.execute(horas_q)).one()

    # Vacaciones / ausencias
    vac_pend_q = select(func.count()).where(
        LeaveRequest.tenant_id == tenant_id,
        LeaveRequest.status == "pending",
    )
    vac_pendientes = int((await db.execute(vac_pend_q)).scalar() or 0)

    vac_aprob_q = select(func.count()).where(
        LeaveRequest.tenant_id == tenant_id,
        LeaveRequest.status == "approved",
        LeaveRequest.start_date <= end,
        LeaveRequest.end_date >= start,
    )
    vac_aprobadas_periodo = int((await db.execute(vac_aprob_q)).scalar() or 0)

    # Gastos pendientes
    gastos_pend_q = select(
        func.count(),
        func.coalesce(func.sum(Expense.amount), 0),
    ).where(
        Expense.tenant_id == tenant_id,
        Expense.status == "pending",
    )
    gastos_pend_n, gastos_pend_imp = (await db.execute(gastos_pend_q)).one()

    # ── IA: desglose por agente (AgentExecutionTrace en el periodo) ──────
    period_start_dt = datetime.combine(start, datetime.min.time())
    period_end_dt = datetime.combine(end, datetime.max.time())

    # ── Inventario: bajas/mermas (unidades) + bajo mínimo del periodo ────
    # Baja = salida con motivo (reason no nulo), sólo unidades (stock_kind unit).
    # Valor = unidades * coste (unit_cost del movimiento → cost_price → 0).
    bajas_q = (
        select(
            func.coalesce(func.sum(func.abs(StockMovement.quantity)), 0),
            func.coalesce(
                func.sum(
                    func.abs(StockMovement.quantity)
                    * func.coalesce(StockMovement.unit_cost, Product.cost_price, 0)
                ),
                0,
            ),
        )
        .select_from(StockMovement)
        .join(Product, Product.id == StockMovement.product_id)
        .where(
            StockMovement.tenant_id == tenant_id,
            StockMovement.movement_type == "salida",
            StockMovement.reason.is_not(None),
            StockMovement.stock_kind == "unit",
            StockMovement.created_at >= period_start_dt,
            StockMovement.created_at <= period_end_dt,
        )
    )
    bajas_units_t, bajas_value_t = (await db.execute(bajas_q)).one()

    below_min_q = select(func.count()).where(
        Product.tenant_id == tenant_id,
        Product.is_active.is_(True),
        Product.stock_min_alert > 0,
        Product.stock_quantity <= Product.stock_min_alert,
    )
    below_min_count = int((await db.execute(below_min_q)).scalar() or 0)

    # Estado de stock ACTUAL: nº de productos activos, unidades en stock y valor a
    # coste (Σ stock_quantity × cost_price). Antes la analítica solo reflejaba
    # bajas/merma y bajo-mínimo, no el estado real del inventario (A6).
    stock_q = select(
        func.count(Product.id),
        func.coalesce(func.sum(Product.stock_quantity), 0),
        func.coalesce(
            func.sum(Product.stock_quantity * func.coalesce(Product.cost_price, 0)), 0
        ),
    ).where(Product.tenant_id == tenant_id, Product.is_active.is_(True))
    productos_activos, unidades_stock, valor_stock = (await db.execute(stock_q)).one()

    agent_q = (
        select(
            AgentExecutionTrace.agent_name,
            func.count().label("n"),
            func.sum(case((AgentExecutionTrace.status == "ok", 1), else_=0)).label("ok_n"),
            func.coalesce(func.sum(AgentExecutionTrace.tokens_in), 0).label("tin"),
            func.coalesce(func.sum(AgentExecutionTrace.tokens_out), 0).label("tout"),
            func.coalesce(func.sum(AgentExecutionTrace.cost_eur), 0).label("cost"),
            func.coalesce(func.avg(AgentExecutionTrace.duration_ms), 0).label("avg_ms"),
        )
        .where(
            AgentExecutionTrace.tenant_id == tenant_id,
            AgentExecutionTrace.created_at >= period_start_dt,
            AgentExecutionTrace.created_at <= period_end_dt,
        )
        .group_by(AgentExecutionTrace.agent_name)
        .order_by(desc("n"))
        .limit(10)
    )
    ia_por_agente = []
    tokens_total_periodo = 0
    coste_total_periodo = 0.0
    tiempo_total_ms = 0.0
    tiempo_total_n = 0
    for agent, n, ok_n, tin, tout, cost, avg_ms in (await db.execute(agent_q)).all():
        n_int = int(n or 0)
        ok_int = int(ok_n or 0)
        ia_por_agente.append({
            "agent": agent or "desconocido",
            "ejecuciones": n_int,
            "exito_pct": round((ok_int / n_int) * 100, 1) if n_int > 0 else 0.0,
            "tokens_in": int(tin or 0),
            "tokens_out": int(tout or 0),
            "coste_eur": round(float(cost or 0), 4),
            "duracion_media_ms": int(float(avg_ms or 0)),
        })
        tokens_total_periodo += int(tin or 0) + int(tout or 0)
        coste_total_periodo += float(cost or 0)
        tiempo_total_ms += float(avg_ms or 0) * n_int
        tiempo_total_n += n_int

    tiempo_medio_ms = int(tiempo_total_ms / tiempo_total_n) if tiempo_total_n > 0 else 0

    # Top errores (error_class) del periodo
    err_q = (
        select(
            AgentExecutionTrace.error_class,
            func.count().label("n"),
        )
        .where(
            AgentExecutionTrace.tenant_id == tenant_id,
            AgentExecutionTrace.status == "error",
            AgentExecutionTrace.created_at >= period_start_dt,
            AgentExecutionTrace.created_at <= period_end_dt,
            AgentExecutionTrace.error_class.is_not(None),
        )
        .group_by(AgentExecutionTrace.error_class)
        .order_by(desc("n"))
        .limit(5)
    )
    top_errores_ia = [
        {"error": ec or "desconocido", "count": int(n or 0)}
        for ec, n in (await db.execute(err_q)).all()
    ]

    # ── Empty-state flag (no hay facturas registradas) ───────────────────
    is_empty = emitidas_count == 0 and recibidas_count == 0

    return {
        "period": period,
        "period_label": _period_label(start),
        "generated_at": datetime.now(UTC).isoformat(),
        "is_empty": is_empty,
        "facturas": {
            "total_ingresos": round(total_ingresos, 2),
            "total_gastos": round(total_gastos, 2),
            "beneficio": round(beneficio, 2),
            "margen_pct": margen_pct,
            "ingresos_periodo": round(ingresos_periodo, 2),
            "gastos_periodo": round(gastos_periodo, 2),
            "beneficio_periodo": round(beneficio_periodo, 2),
            "margen_periodo_pct": margen_periodo_pct,
            "emitidas_count": emitidas_count,
            "recibidas_count": recibidas_count,
            "emitidas_periodo": int(emitidas_periodo or 0),
            "recibidas_periodo": int(recibidas_periodo or 0),
            "pagadas_count": pagadas_count,
            "pendientes_count": pendientes_count,
            "borradores_count": borradores_count,
            "canceladas_count": canceladas_count,
            "importe_pendiente_cobro": round(importe_pendiente_cobro, 2),
            "importe_pendiente_pago": round(importe_pendiente_pago, 2),
            "vencen_proximos_7d": vencen_proximos_count,
            "importe_vencen_proximos_7d": round(vencen_proximos_amount, 2),
            "ticket_medio_periodo": ticket_medio_periodo,
        },
        "ventas_detalle": {
            "iva_breakdown": iva_breakdown,
            "top_productos": top_productos,
            "por_dia_semana": por_dia_semana,
        },
        "cobros_pagos": {
            "aging_cobros": aging_cobros,
            "aging_pagos": aging_pagos,
            "dso_dias": dso_dias,
            "dpo_dias": dpo_dias,
        },
        "cashflow": cashflow,
        "top_clientes": top_clientes,
        "estado_facturas": estado_facturas,
        "rrhh": {
            "empleados_activos": empleados_activos,
            "coste_nominas_periodo": round(coste_nominas, 2),
            "coste_medio_empleado": coste_medio_empleado,
            "nominas_pagadas": nominas_pagadas,
            "nominas_pendientes": nominas_pendientes,
            "por_departamento": rrhh_por_departamento,
            "horas_ordinarias_periodo": round(float(horas_ord_t or 0), 2),
            "horas_extra_periodo": round(float(horas_ext_t or 0), 2),
            "vacaciones_pendientes": vac_pendientes,
            "vacaciones_aprobadas_periodo": vac_aprobadas_periodo,
            "gastos_pendientes_count": int(gastos_pend_n or 0),
            "gastos_pendientes_importe": round(float(gastos_pend_imp or 0), 2),
        },
        "banca": {
            "saldo_actual": round(saldo_actual, 2),
            "entradas_periodo": round(entradas_periodo, 2),
            "salidas_periodo": round(salidas_periodo, 2),
            "transacciones_periodo": transacciones_periodo,
            "reconciliadas": reconciliadas,
            "pendientes_conciliar": pendientes_conciliar,
            "has_demo_data": has_demo_data,
        },
        "inventario": {
            "productos_activos": int(productos_activos or 0),
            "unidades_stock": int(unidades_stock or 0),
            "valor_stock_eur": round(float(valor_stock or 0), 2),
            "bajas_units": int(bajas_units_t or 0),
            "bajas_value_eur": round(float(bajas_value_t or 0), 2),
            "below_min_count": below_min_count,
        },
        "ia": {
            "tasks_total": tasks_total,
            "tasks_done": tasks_done,
            "tasks_failed": tasks_failed,
            "tasks_pending": tasks_pending,
            "tasks_success_rate": tasks_success_rate,
            "tasks_periodo": tasks_periodo,
            "tokens_total_periodo": tokens_total_periodo,
            "coste_total_periodo_eur": round(coste_total_periodo, 4),
            "tiempo_medio_ms": tiempo_medio_ms,
        },
        "ia_detalle": {
            "por_agente": ia_por_agente,
            "top_errores": top_errores_ia,
        },
        "clientes": {
            "total": total_clientes,
            "nuevos_periodo": nuevos_clientes_periodo,
        },
    }
