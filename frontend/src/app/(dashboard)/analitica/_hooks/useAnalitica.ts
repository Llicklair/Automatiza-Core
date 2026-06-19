"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api, type AnalyticsAgingBuckets, type AnalyticsDashboard } from "@/lib/api";

export type { AnalyticsCashflowEntry as CashflowEntry } from "@/lib/api";

const EMPTY_AGING: AnalyticsAgingBuckets = {
    vencido_90: { n: 0, importe: 0 },
    vencido_60_90: { n: 0, importe: 0 },
    vencido_30_60: { n: 0, importe: 0 },
    vencido_0_30: { n: 0, importe: 0 },
    vence_0_30: { n: 0, importe: 0 },
    vence_30plus: { n: 0, importe: 0 },
};

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
        importe_pendiente_cobro: 0, importe_pendiente_pago: 0,
        vencen_proximos_7d: 0, importe_vencen_proximos_7d: 0,
        ticket_medio_periodo: 0,
    },
    ventas_detalle: { iva_breakdown: [], top_productos: [], por_dia_semana: [] },
    cobros_pagos: { aging_cobros: EMPTY_AGING, aging_pagos: EMPTY_AGING, dso_dias: 0, dpo_dias: 0 },
    cashflow: [],
    top_clientes: [],
    estado_facturas: [],
    rrhh: {
        empleados_activos: 0, coste_nominas_periodo: 0, coste_medio_empleado: 0,
        nominas_pagadas: 0, nominas_pendientes: 0, por_departamento: [],
        horas_ordinarias_periodo: 0, horas_extra_periodo: 0,
        vacaciones_pendientes: 0, vacaciones_aprobadas_periodo: 0,
        gastos_pendientes_count: 0, gastos_pendientes_importe: 0,
    },
    banca: {
        saldo_actual: 0, entradas_periodo: 0, salidas_periodo: 0,
        transacciones_periodo: 0, reconciliadas: 0, pendientes_conciliar: 0, has_demo_data: false,
    },
    ia: {
        tasks_total: 0, tasks_done: 0, tasks_failed: 0, tasks_pending: 0,
        tasks_success_rate: 0, tasks_periodo: 0,
        tokens_total_periodo: 0, coste_total_periodo_eur: 0, tiempo_medio_ms: 0,
    },
    ia_detalle: { por_agente: [], top_errores: [] },
    clientes: { total: 0, nuevos_periodo: 0 },
};

export function useAnalitica() {
    const t = useTranslations("analitica");
    // Vacío = no enviar periodo → el backend abre en el último mes con datos
    // (evita el dashboard "vacío" a principio de mes). Se sincroniza con la
    // respuesta en la primera carga; luego el selector manda.
    const [period, setPeriod] = useState<string>("");
    const [data, setData] = useState<AnalyticsDashboard>(EMPTY_DASHBOARD);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchDashboard = useCallback((p: string) => {
        setLoading(true);
        setError(null);
        api.analytics.dashboard(p)
            .then((d) => {
                setData(d);
                // En la carga inicial (period vacío) adoptamos el periodo que
                // eligió el backend (último mes con datos) para el selector.
                setPeriod((prev) => prev || d.period);
            })
            .catch((e: Error) => {
                setError(e.message || t("page.loadError"));
                setData(EMPTY_DASHBOARD);
            })
            .finally(() => setLoading(false));
    }, [t]);

    useEffect(() => {
        fetchDashboard(period);
    }, [period, fetchDashboard]);

    return {
        period,
        setPeriod,
        loading,
        error,
        refresh: () => fetchDashboard(period),

        data,

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
        importePendientePago: data.facturas.importe_pendiente_pago,
        ticketMedio: data.facturas.ticket_medio_periodo,
        vencenProximos: data.facturas.vencen_proximos_7d,
        importeVencenProximos: data.facturas.importe_vencen_proximos_7d,
        topClientes: data.top_clientes,
        pieData: data.estado_facturas,
        ventasDetalle: data.ventas_detalle,
        cobrosPagos: data.cobros_pagos,
        rrhh: data.rrhh,
        banca: data.banca,
        ia: data.ia,
        iaDetalle: data.ia_detalle,
        tasksDone: data.ia.tasks_done,
        tasksFailed: data.ia.tasks_failed,
        tasksSuccessRate: data.ia.tasks_success_rate,
        tasksPending: data.ia.tasks_pending,
        tasksPeriodo: data.ia.tasks_periodo,
        periodLabel: data.period_label,
    };
}
