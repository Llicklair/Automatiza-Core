/**
 * MOD.130/347/390/111/190 — cliente de los endpoints de cálculo de modelos AEAT.
 *
 * El backend devuelve un dict con la liquidación pre-calculada. El frontend
 * lo presenta como preview en `/impuestos`. La presentación real (firmada
 * + telemática) corre por PRES.303 / PRES.MOD1/MOD2 (post-DEC.14).
 */
import { request } from "./client";

export interface ModeloAeatResult {
    [key: string]: unknown;
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
};
