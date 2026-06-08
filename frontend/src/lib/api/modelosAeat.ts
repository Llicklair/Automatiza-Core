/**
 * MOD.130/347/390/111/190 — cliente de los endpoints de cálculo de modelos AEAT.
 *
 * El backend devuelve un dict con la liquidación pre-calculada. El frontend
 * lo presenta como preview en `/impuestos`. La presentación real (firmada
 * + telemática) corre por PRES.303 / PRES.MOD1/MOD2 (post-DEC.14).
 */
import { downloadBlob, request } from "./client";

/** Descarga del PDF borrador imprimible de cada modelo. */
const _q = (quarter: number, year?: number) =>
    `quarter=${quarter}${year ? `&year=${year}` : ""}`;
const _y = (year?: number) => (year ? `?year=${year}` : "");

export const modelosPdf = {
    m303: (quarter: number, year?: number) =>
        downloadBlob(`/api/v1/reports/modelos/303/pdf?${_q(quarter, year)}`,
            `modelo-303-${quarter}T-${year ?? ""}.pdf`),
    m130: (quarter: number, year?: number) =>
        downloadBlob(`/api/v1/reports/modelos/130/pdf?${_q(quarter, year)}`,
            `modelo-130-${quarter}T-${year ?? ""}.pdf`),
    m111: (quarter: number, year?: number) =>
        downloadBlob(`/api/v1/reports/modelos/111/pdf?${_q(quarter, year)}`,
            `modelo-111-${quarter}T-${year ?? ""}.pdf`),
    m115: (quarter: number, year?: number) =>
        downloadBlob(`/api/v1/reports/modelos/115/pdf?${_q(quarter, year)}`,
            `modelo-115-${quarter}T-${year ?? ""}.pdf`),
    m349: (quarter: number, year?: number) =>
        downloadBlob(`/api/v1/reports/modelos/349/pdf?${_q(quarter, year)}`,
            `modelo-349-${quarter}T-${year ?? ""}.pdf`),
    m190: (year?: number) =>
        downloadBlob(`/api/v1/reports/modelos/190/pdf${_y(year)}`, `modelo-190-${year ?? ""}.pdf`),
    m347: (year?: number) =>
        downloadBlob(`/api/v1/reports/modelos/347/pdf${_y(year)}`, `modelo-347-${year ?? ""}.pdf`),
    m390: (year?: number) =>
        downloadBlob(`/api/v1/reports/modelos/390/pdf${_y(year)}`, `modelo-390-${year ?? ""}.pdf`),
};

export interface ModeloAeatResult {
    [key: string]: unknown;
}

export type PreventiveSeverity = "high" | "medium" | "low";

export interface PreventiveFinding {
    code: string;
    severity: PreventiveSeverity;
    message: string;
    suggested_action: string;
    source_invoice_ids: string[];
}

export interface PreventiveCheckResult {
    quarter: number;
    year: number;
    findings: PreventiveFinding[];
    count_by_severity: Record<PreventiveSeverity, number>;
}

export const modelosAeat = {
    /** Modelo 130 — IRPF estimación directa, trimestral. */
    m130: (quarter: number, year?: number) => {
        const qs = new URLSearchParams({ quarter: String(quarter) });
        if (year) qs.append("year", String(year));
        return request<ModeloAeatResult>(`/api/v1/reports/modelos/130?${qs}`);
    },

    /** Modelo 111 — Retenciones trabajadores, trimestral. */
    m111: (quarter: number, year?: number) => {
        const qs = new URLSearchParams({ quarter: String(quarter) });
        if (year) qs.append("year", String(year));
        return request<ModeloAeatResult>(`/api/v1/reports/modelos/111?${qs}`);
    },

    /** Modelo 190 — Resumen anual retenciones (4×111). */
    m190: (year?: number) => {
        const qs = new URLSearchParams();
        if (year) qs.append("year", String(year));
        return request<ModeloAeatResult>(
            `/api/v1/reports/modelos/190${qs.toString() ? "?" + qs : ""}`,
        );
    },

    /** Modelo 347 — Operaciones con terceros >3.005,06€, anual. */
    m347: (year?: number) => {
        const qs = new URLSearchParams();
        if (year) qs.append("year", String(year));
        return request<ModeloAeatResult>(
            `/api/v1/reports/modelos/347${qs.toString() ? "?" + qs : ""}`,
        );
    },

    /** Modelo 390 — Resumen anual IVA (4×303). */
    m390: (year?: number) => {
        const qs = new URLSearchParams();
        if (year) qs.append("year", String(year));
        return request<ModeloAeatResult>(
            `/api/v1/reports/modelos/390${qs.toString() ? "?" + qs : ""}`,
        );
    },

    /** Modelo 200 — Impuesto sobre Sociedades (preview anual, F2.8). */
    m200: (
        year?: number,
        opts?: { tipo_impositivo_pct?: number; pagos_fraccionados_pagados?: number },
    ) => {
        const qs = new URLSearchParams();
        if (year) qs.append("year", String(year));
        if (opts?.tipo_impositivo_pct !== undefined)
            qs.append("tipo_impositivo_pct", String(opts.tipo_impositivo_pct));
        if (opts?.pagos_fraccionados_pagados !== undefined)
            qs.append("pagos_fraccionados_pagados", String(opts.pagos_fraccionados_pagados));
        return request<ModeloAeatResult>(
            `/api/v1/reports/modelos/200${qs.toString() ? "?" + qs : ""}`,
        );
    },

    /** Asistente fiscal preventivo — riesgos antes de cerrar el 303. */
    preventiveCheck: (quarter: number, year?: number) => {
        const qs = new URLSearchParams({ quarter: String(quarter) });
        if (year) qs.append("year", String(year));
        return request<PreventiveCheckResult>(
            `/api/v1/reports/modelos/preventive-check?${qs}`,
        );
    },

    /** Descarga de PDF borrador imprimible por modelo. */
    pdf: modelosPdf,
};
