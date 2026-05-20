import { downloadBlob, request } from "./client";

export interface JournalLine {
    id: string;
    tenant_id: string;
    entry_id: string;
    account_code: string;
    account_name: string | null;
    debit: number;
    credit: number;
}

export interface JournalEntry {
    id: string;
    tenant_id: string;
    date: string;
    description: string;
    reference_id: string | null;
    created_at: string;
    lines: JournalLine[];
}

export interface FixedAsset {
    id: string;
    tenant_id: string;
    name: string;
    category: string | null;
    description: string | null;
    purchase_date: string;
    purchase_value: number;
    useful_life_years: number;
    residual_value: number;
    depreciation_method: string;
    status: string;
    account_code: string | null;
    reference_invoice: string | null;
    notes: string | null;
    created_at: string;
}

export type AccountingPeriodKind = "month" | "quarter" | "year";

export interface AccountingPeriod {
    id: string;
    year: number;
    kind: AccountingPeriodKind;
    period_index: number;
    status: "closed" | "reopened";
    closed_at: string | null;
    reopened_at: string | null;
    reopen_reason: string | null;
    notes: string | null;
}

export const accounting = {
    journal: {
        list: () => request<JournalEntry[]>("/api/v1/accounting/journal"),
        create: (data: Partial<JournalEntry>) => request<JournalEntry>("/api/v1/accounting/journal", { method: "POST", body: JSON.stringify(data) }),
        delete: (id: string) => request(`/api/v1/accounting/journal/${id}`, { method: "DELETE" }),
    },
    assets: {
        list: () => request<FixedAsset[]>("/api/v1/accounting/assets"),
        create: (data: Partial<FixedAsset>) => request<FixedAsset>("/api/v1/accounting/assets", { method: "POST", body: JSON.stringify(data) }),
        update: (id: string, data: Partial<FixedAsset>) => request<FixedAsset>(`/api/v1/accounting/assets/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
        delete: (id: string) => request(`/api/v1/accounting/assets/${id}`, { method: "DELETE" }),
    },
    periods: {
        list: (year?: number) =>
            request<{ items: AccountingPeriod[] }>(`/api/v1/accounting/periods${year ? `?year=${year}` : ""}`),
        close: (data: { year: number; kind: AccountingPeriodKind; period_index: number; notes?: string }) =>
            request<AccountingPeriod>("/api/v1/accounting/periods/close", {
                method: "POST",
                body: JSON.stringify(data),
            }),
        reopen: (id: string, reason: string) =>
            request<AccountingPeriod>(`/api/v1/accounting/periods/${id}/reopen`, {
                method: "POST",
                body: JSON.stringify({ reason }),
            }),
        checkLocked: (target: string) =>
            request<{ locked: boolean; period_label: string | null }>(`/api/v1/accounting/check-locked?target=${target}`),
    },
    libroDiarioPdf: (start: string, end: string) =>
        downloadBlob(`/api/v1/accounting/libro-diario.pdf?start=${start}&end=${end}`,
            `LibroDiario_${start}_${end}.pdf`),
    libroMayorPdf: (start: string, end: string) =>
        downloadBlob(`/api/v1/accounting/libro-mayor.pdf?start=${start}&end=${end}`,
            `LibroMayor_${start}_${end}.pdf`),
    cuentasAnualesPdf: (start: string, end: string) =>
        downloadBlob(`/api/v1/accounting/cuentas-anuales.pdf?start=${start}&end=${end}`,
            `CuentasAnuales_${start}_${end}.pdf`),
};
