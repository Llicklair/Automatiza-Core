import { request, downloadBlob } from "./client";

export interface CompanySnapshot {
    month: string;
    generated_at: string;
    facturas: {
        ingresos_total: number;
        gastos_total: number;
        margen_bruto: number;
        margen_pct: number;
        facturas_emitidas: number;
        facturas_recibidas: number;
        facturas_pendientes_cobro: number;
        importe_pendiente_cobro: number;
    };
    banca: {
        total_ingresos: number;
        total_gastos: number;
        saldo_neto: number;
        transacciones: number;
        reconciliadas: number;
    };
    rrhh: {
        empleados_activos: number;
        coste_nominas: number;
        nominas_pagadas: number;
        nominas_pendientes: number;
    };
    clientes: {
        total_clientes: number;
        nuevos_periodo: number;
        top_client_name: string | null;
        top_client_amount: number;
    };
    resumen_ejecutivo: string;
}

export interface ReportDoc {
    id: string;
    file_name: string;
    file_size: number;
    category: string | null;
    created_at: string;
}

export const reports = {
    snapshot: (month?: string) =>
        request<CompanySnapshot>(`/api/v1/reports/company-snapshot${month ? `?month=${month}` : ""}`),
    generate: (month?: string) =>
        request<ReportDoc>(`/api/v1/reports/company-snapshot/generate${month ? `?month=${month}` : ""}`, { method: "POST" }),
    list: () => request<ReportDoc[]>("/api/v1/reports/"),
    download: (id: string, filename: string) => downloadBlob(`/api/v1/reports/${id}/download`, filename),
    libroRegistro: (year: number, type: "emitidas" | "recibidas" = "emitidas") =>
        downloadBlob(`/api/v1/reports/libro-registro?year=${year}&type=${type}`, `LibroRegistro_${type}_${year}.csv`),
};

export const advisory = {
    boe: (section: string = "fiscal", limit: number = 10) =>
        request<any[]>(`/api/v1/advisory/boe?section=${section}&limit=${limit}`),
    calendar: (days_ahead: number = 60) =>
        request<any[]>(`/api/v1/advisory/calendar?days_ahead=${days_ahead}`),
    guides: (section: string = "fiscal") =>
        request<any[]>(`/api/v1/advisory/guides?section=${section}`),
};
