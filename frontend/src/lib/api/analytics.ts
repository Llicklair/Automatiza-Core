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
    importe_pendiente_pago: number;
    vencen_proximos_7d: number;
    importe_vencen_proximos_7d: number;
    ticket_medio_periodo: number;
}

export interface AnalyticsIVAEntry {
    rate: number;
    base: number;
    iva: number;
    total: number;
}

export interface AnalyticsTopProducto {
    name: string;
    cantidad: number;
    total: number;
}

export interface AnalyticsDiaSemana {
    dia: string;
    ingresos: number;
    n: number;
}

export interface AnalyticsVentasDetalle {
    iva_breakdown: AnalyticsIVAEntry[];
    top_productos: AnalyticsTopProducto[];
    por_dia_semana: AnalyticsDiaSemana[];
}

export interface AnalyticsAgingBucket {
    n: number;
    importe: number;
}

export type AgingBucketKey =
    | "vencido_90"
    | "vencido_60_90"
    | "vencido_30_60"
    | "vencido_0_30"
    | "vence_0_30"
    | "vence_30plus";

export type AnalyticsAgingBuckets = Record<AgingBucketKey, AnalyticsAgingBucket>;

export interface AnalyticsCobrosPagos {
    aging_cobros: AnalyticsAgingBuckets;
    aging_pagos: AnalyticsAgingBuckets;
    dso_dias: number;
    dpo_dias: number;
}

export interface AnalyticsRRHHDept {
    departamento: string;
    empleados: number;
    coste_base: number;
}

export interface AnalyticsRRHH {
    empleados_activos: number;
    coste_nominas_periodo: number;
    coste_medio_empleado: number;
    nominas_pagadas: number;
    nominas_pendientes: number;
    por_departamento: AnalyticsRRHHDept[];
    horas_ordinarias_periodo: number;
    horas_extra_periodo: number;
    vacaciones_pendientes: number;
    vacaciones_aprobadas_periodo: number;
    gastos_pendientes_count: number;
    gastos_pendientes_importe: number;
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
    tokens_total_periodo: number;
    coste_total_periodo_eur: number;
    tiempo_medio_ms: number;
}

export interface AnalyticsIAAgente {
    agent: string;
    ejecuciones: number;
    exito_pct: number;
    tokens_in: number;
    tokens_out: number;
    coste_eur: number;
    duracion_media_ms: number;
}

export interface AnalyticsIATopError {
    error: string;
    count: number;
}

export interface AnalyticsIADetalle {
    por_agente: AnalyticsIAAgente[];
    top_errores: AnalyticsIATopError[];
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
    ventas_detalle: AnalyticsVentasDetalle;
    cobros_pagos: AnalyticsCobrosPagos;
    cashflow: AnalyticsCashflowEntry[];
    top_clientes: AnalyticsTopCliente[];
    estado_facturas: AnalyticsEstadoFactura[];
    rrhh: AnalyticsRRHH;
    banca: AnalyticsBanca;
    ia: AnalyticsIA;
    ia_detalle: AnalyticsIADetalle;
    clientes: AnalyticsClientes;
}

export const analytics = {
    dashboard: (period?: string) => {
        const q = period ? `?period=${encodeURIComponent(period)}` : "";
        return request<AnalyticsDashboard>(`/api/v1/analytics/dashboard${q}`);
    },
};
