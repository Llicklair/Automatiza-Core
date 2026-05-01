import { request } from "./client";

export interface AnalyticsCashflowEntry {
    month: string;
    ingresos: number;
    gastos: number;
    beneficio: number;
}

export interface AnalyticsTopCliente {
    name: string;
    total: number;
}

export interface AnalyticsEstadoFactura {
    name: string;
    value: number;
}

export interface AnalyticsFacturas {
    total_ingresos: number;
    total_gastos: number;
    beneficio: number;
    margen_pct: number;
    ingresos_periodo: number;
    gastos_periodo: number;
    beneficio_periodo: number;
    margen_periodo_pct: number;
    emitidas_count: number;
    recibidas_count: number;
    emitidas_periodo: number;
    recibidas_periodo: number;
    pagadas_count: number;
    pendientes_count: number;
    borradores_count: number;
    canceladas_count: number;
    importe_pendiente_cobro: number;
    vencen_proximos_7d: number;
    importe_vencen_proximos_7d: number;
}

export interface AnalyticsRRHH {
    empleados_activos: number;
    coste_nominas_periodo: number;
    nominas_pagadas: number;
    nominas_pendientes: number;
}

export interface AnalyticsBanca {
    saldo_actual: number;
    entradas_periodo: number;
    salidas_periodo: number;
    transacciones_periodo: number;
    reconciliadas: number;
    pendientes_conciliar: number;
    has_demo_data: boolean;
}

export interface AnalyticsIA {
    tasks_total: number;
    tasks_done: number;
    tasks_failed: number;
    tasks_pending: number;
    tasks_success_rate: number;
    tasks_periodo: number;
}

export interface AnalyticsClientes {
    total: number;
    nuevos_periodo: number;
}

export interface AnalyticsDashboard {
    period: string;
    period_label: string;
    generated_at: string;
    is_empty: boolean;
    facturas: AnalyticsFacturas;
    cashflow: AnalyticsCashflowEntry[];
    top_clientes: AnalyticsTopCliente[];
    estado_facturas: AnalyticsEstadoFactura[];
    rrhh: AnalyticsRRHH;
    banca: AnalyticsBanca;
    ia: AnalyticsIA;
    clientes: AnalyticsClientes;
}

export const analytics = {
    dashboard: (period?: string) => {
        const q = period ? `?period=${encodeURIComponent(period)}` : "";
        return request<AnalyticsDashboard>(`/api/v1/analytics/dashboard${q}`);
    },
};
