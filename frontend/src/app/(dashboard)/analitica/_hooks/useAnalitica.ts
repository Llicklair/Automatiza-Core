"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type AnalyticsDashboard } from "@/lib/api";

export type { AnalyticsCashflowEntry as CashflowEntry } from "@/lib/api";

const EMPTY_DASHBOARD: AnalyticsDashboard = {
    period: "",
    period_label: "",
    generated_at: "",
    is_empty: true,
    facturas: {
        total_ingresos: 0, total_gastos: 0, beneficio: 0, margen_pct: 0,
        ingresos_periodo: 0, gastos_periodo: 0, beneficio_periodo: 0, margen_periodo_pct: 0,
        emitidas_count: 0, recibidas_count: 0, emitidas_periodo: 0, recibidas_periodo: 0,
        pagadas_count: 0, pendientes_count: 0, borradores_count: 0, canceladas_count: 0,
        importe_pendiente_cobro: 0, vencen_proximos_7d: 0, importe_vencen_proximos_7d: 0,
    },
    cashflow: [],
    top_clientes: [],
    estado_facturas: [],
    rrhh: { empleados_activos: 0, coste_nominas_periodo: 0, nominas_pagadas: 0, nominas_pendientes: 0 },
    banca: {
        saldo_actual: 0, entradas_periodo: 0, salidas_periodo: 0,
        transacciones_periodo: 0, reconciliadas: 0, pendientes_conciliar: 0, has_demo_data: false,
    },
    ia: { tasks_total: 0, tasks_done: 0, tasks_failed: 0, tasks_pending: 0, tasks_success_rate: 0, tasks_periodo: 0 },
    clientes: { total: 0, nuevos_periodo: 0 },
};

function currentMonth(): string {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export function useAnalitica() {
    const [period, setPeriod] = useState<string>(currentMonth());
    const [data, setData] = useState<AnalyticsDashboard>(EMPTY_DASHBOARD);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchDashboard = useCallback((p: string) => {
        setLoading(true);
        setError(null);
        api.analytics.dashboard(p)
            .then(setData)
            .catch((e: Error) => {
                setError(e.message || "Error cargando analítica");
                setData(EMPTY_DASHBOARD);
            })
            .finally(() => setLoading(false));
    }, []);

    useEffect(() => {
        fetchDashboard(period);
    }, [period, fetchDashboard]);

    return {
        // controls
        period,
        setPeriod,
        loading,
        error,
        refresh: () => fetchDashboard(period),

        // raw response
        data,

        // legacy-style aliases (so page.tsx can stay close to its current shape)
        isDemo: data.is_empty,
        cashflow: data.cashflow,
        totalIngresos: data.facturas.total_ingresos,
        totalGastos: data.facturas.total_gastos,
        beneficio: data.facturas.beneficio,
        margen: data.facturas.margen_pct,
        ingresosPeriodo: data.facturas.ingresos_periodo,
        gastosPeriodo: data.facturas.gastos_periodo,
        beneficioPeriodo: data.facturas.beneficio_periodo,
        margenPeriodo: data.facturas.margen_periodo_pct,
        emitidasCount: data.facturas.emitidas_count,
        recibidasCount: data.facturas.recibidas_count,
        factPagadas: data.facturas.pagadas_count,
        factPendientes: data.facturas.pendientes_count,
        factBorrador: data.facturas.borradores_count,
        importePendienteCobro: data.facturas.importe_pendiente_cobro,
        vencenProximos: data.facturas.vencen_proximos_7d,
        importeVencenProximos: data.facturas.importe_vencen_proximos_7d,
        topClientes: data.top_clientes,
        pieData: data.estado_facturas,
        rrhh: data.rrhh,
        banca: data.banca,
        tasksDone: data.ia.tasks_done,
        tasksFailed: data.ia.tasks_failed,
        tasksSuccessRate: data.ia.tasks_success_rate,
        tasksPending: data.ia.tasks_pending,
        tasksPeriodo: data.ia.tasks_periodo,
        periodLabel: data.period_label,
    };
}
