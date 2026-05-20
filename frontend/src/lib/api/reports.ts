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

export interface FiscalSnapshot {
    period: string;
    period_label: string;
    generated_at: string;
    iva: {
        repercutido_21: number;
        repercutido_10: number;
        repercutido_4: number;
        total_repercutido: number;
        base_repercutido: number;
        soportado_21: number;
        soportado_10: number;
        soportado_4: number;
        total_soportado: number;
        base_soportado: number;
        resultado_iva: number;
    };
    irpf: {
        retenciones_nominas: number;
        retenciones_facturas: number;
        total_retenciones: number;
    };
    impuesto_sociedades: {
        ingresos_brutos: number;
        gastos_deducibles: number;
        base_imponible: number;
        tipo_estimado: number;
        cuota_estimada: number;
    };
    resumen_ejecutivo: string;
}

export interface Casilla303 {
    codigo: string;
    descripcion: string;
    valor: number;
    editable: boolean;
    nota: string | null;
}

export interface ChecklistStep {
    n: number;
    titulo: string;
    detalle: string;
    completado: boolean;
}

export interface Modelo303Expediente {
    tenant: { name: string; nif: string };
    quarter: number;
    year: number;
    periodo: string;
    casillas: Casilla303[];
    resumen: {
        total_devengado: number;
        total_deducible: number;
        resultado: number;
        signo: "ingresar" | "compensar" | "cero";
    };
    xml: string;
    xml_filename: string;
    xml_base64: string;
    pdf_url: string;
    checklist: ChecklistStep[];
}

export const reports = {
    snapshot: (month?: string) =>
        request<CompanySnapshot>(`/api/v1/reports/company-snapshot${month ? `?month=${month}` : ""}`),
    generate: (month?: string) =>
        request<ReportDoc>(`/api/v1/reports/company-snapshot/generate${month ? `?month=${month}` : ""}`, { method: "POST" }),
    fiscalSnapshot: (period?: string) =>
        request<FiscalSnapshot>(`/api/v1/reports/fiscal-snapshot${period ? `?period=${period}` : ""}`),
    generateFiscal: (period?: string) =>
        request<ReportDoc>(`/api/v1/reports/fiscal-snapshot/generate${period ? `?period=${period}` : ""}`, { method: "POST" }),
    list: () => request<ReportDoc[]>("/api/v1/reports/"),
    download: (id: string, filename: string) => downloadBlob(`/api/v1/reports/${id}/download`, filename),
    delete: (id: string) => request(`/api/v1/reports/${id}`, { method: "DELETE" }),
    libroRegistro: (year: number, type: "emitidas" | "recibidas" = "emitidas") =>
        downloadBlob(`/api/v1/reports/libro-registro?year=${year}&type=${type}`, `LibroRegistro_${type}_${year}.csv`),
    modelo303Pdf: (quarter: number, year: number) =>
        downloadBlob(`/api/v1/reports/modelo-303?quarter=${quarter}&year=${year}`, `Modelo303_Q${quarter}_${year}.pdf`),
    modelo303Expediente: (quarter: number, year: number) =>
        request<Modelo303Expediente>(`/api/v1/reports/modelo-303/expediente?quarter=${quarter}&year=${year}`),
};

export const advisory = {
    boe: (section: string = "fiscal", limit: number = 10) =>
        request<any[]>(`/api/v1/advisory/boe?section=${section}&limit=${limit}`),
    calendar: (days_ahead: number = 60) =>
        request<any[]>(`/api/v1/advisory/calendar?days_ahead=${days_ahead}`),
    guides: (section: string = "fiscal") =>
        request<any[]>(`/api/v1/advisory/guides?section=${section}`),
};
