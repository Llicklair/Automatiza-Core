"""Dashboard analytics aggregation.

Single source of truth for the /analytics/dashboard endpoint.
Returns a complete snapshot for a given period (YYYY-MM): facturas, banca,
RRHH, IA tasks, top clientes, cashflow histórico (6 meses) y estado de
facturas. Demo bank transactions (description prefijada con [DEMO])
quedan excluidas para no contaminar las métricas.

Estados de Invoice válidos según state_machine: draft, issued, paid, cancelled.
"""

from __future__ import annotations

import uuid
from calendar import monthrange
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import desc, func, not_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import (
    BankTransaction,
    Client,
    Employee,
    Invoice,
    Payroll,
    Task,
)

DEMO_TX_PREFIX = "[DEMO]"
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


async def get_dashboard(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    period: str,
    start: date,
    end: date,
) -> dict:
    """Agrega todas las métricas del dashboard para un periodo (YYYY-MM)."""
    today = date.today()

    # ── Facturas: agregaciones del periodo ───────────────────────────────
    issued_period_q = select(
        func.coalesce(func.sum(Invoice.amount_total), 0),
        func.count(),
    ).where(
        Invoice.tenant_id == tenant_id,
        Invoice.invoice_type == "issued",
        Invoice.date >= start,
        Invoice.date <= end,
    )
    received_period_q = select(
        func.coalesce(func.sum(Invoice.amount_total), 0),
        func.count(),
    ).where(
        Invoice.tenant_id == tenant_id,
        Invoice.invoice_type == "received",
        Invoice.date >= start,
        Invoice.date <= end,
    )
    ingresos_periodo_t, emitidas_periodo = (await db.execute(issued_period_q)).one()
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
        Invoice.invoice_type == "issued",
    ).group_by(Invoice.status)
    status_rows = (await db.execute(status_breakdown_q)).all()

    status_counts: dict[str, int] = {}
    status_amounts: dict[str, float] = {}
    for st, cnt, amt in status_rows:
        status_counts[st] = int(cnt or 0)
        status_amounts[st] = float(amt or 0)

    pagadas_count = status_counts.get("paid", 0)
    pendientes_count = status_counts.get("issued", 0)
    borradores_count = status_counts.get("draft", 0)
    canceladas_count = status_counts.get("cancelled", 0)

    importe_pendiente_cobro = status_amounts.get("issued", 0.0)

    total_ingresos_q = select(func.coalesce(func.sum(Invoice.amount_total), 0)).where(
        Invoice.tenant_id == tenant_id,
        Invoice.invoice_type == "issued",
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

    # ── Próximas a vencer (issued + due_date <= hoy+7) ───────────────────
    due_soon_q = select(
        func.count(), func.coalesce(func.sum(Invoice.amount_total), 0)
    ).where(
        Invoice.tenant_id == tenant_id,
        Invoice.invoice_type == "issued",
        Invoice.status == "issued",
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
            Invoice.invoice_type == "issued",
            Invoice.status != "cancelled",
            Invoice.date >= m_start,
            Invoice.date <= m_end,
        )
        gas_q = select(func.coalesce(func.sum(Invoice.amount_total), 0)).where(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_type == "received",
            Invoice.status != "cancelled",
            Invoice.date >= m_start,
            Invoice.date <= m_end,
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
            Invoice.invoice_type == "issued",
            Invoice.status != "cancelled",
            Invoice.date >= start,
            Invoice.date <= end,
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
    for label, key in (
        ("Cobradas", "paid"),
        ("Pendientes", "issued"),
        ("Borradores", "draft"),
        ("Canceladas", "cancelled"),
    ):
        val = status_amounts.get(key, 0.0)
        if val > 0:
            estado_facturas.append({"name": label, "value": round(val, 2)})

    # ── RRHH ─────────────────────────────────────────────────────────────
    emp_q = select(func.count()).where(
        Employee.tenant_id == tenant_id, Employee.status == "active"
    )
    empleados_activos = int((await db.execute(emp_q)).scalar() or 0)

    payroll_periodo_q = select(Payroll).where(
        Payroll.tenant_id == tenant_id,
        Payroll.period_start >= start,
        Payroll.period_end <= end,
    )
    payrolls = (await db.execute(payroll_periodo_q)).scalars().all()
    coste_nominas = sum(float(p.net_salary or 0) for p in payrolls)
    nominas_pagadas = sum(1 for p in payrolls if p.status == "paid")
    nominas_pendientes = len(payrolls) - nominas_pagadas

    # ── Banca (excluyendo demo) ──────────────────────────────────────────
    bank_period_q = select(BankTransaction).where(
        BankTransaction.tenant_id == tenant_id,
        BankTransaction.date >= start,
        BankTransaction.date <= end,
        _real_tx_filter(),
    )
    bank_txs = (await db.execute(bank_period_q)).scalars().all()
    entradas_periodo = sum(float(t.amount) for t in bank_txs if float(t.amount) > 0)
    salidas_periodo = abs(sum(float(t.amount) for t in bank_txs if float(t.amount) < 0))
    transacciones_periodo = len(bank_txs)
    reconciliadas = sum(1 for t in bank_txs if t.status == "reconciled")
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
            "vencen_proximos_7d": vencen_proximos_count,
            "importe_vencen_proximos_7d": round(vencen_proximos_amount, 2),
        },
        "cashflow": cashflow,
        "top_clientes": top_clientes,
        "estado_facturas": estado_facturas,
        "rrhh": {
            "empleados_activos": empleados_activos,
            "coste_nominas_periodo": round(coste_nominas, 2),
            "nominas_pagadas": nominas_pagadas,
            "nominas_pendientes": nominas_pendientes,
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
        "ia": {
            "tasks_total": tasks_total,
            "tasks_done": tasks_done,
            "tasks_failed": tasks_failed,
            "tasks_pending": tasks_pending,
            "tasks_success_rate": tasks_success_rate,
            "tasks_periodo": tasks_periodo,
        },
        "clientes": {
            "total": total_clientes,
            "nuevos_periodo": nuevos_clientes_periodo,
        },
    }
