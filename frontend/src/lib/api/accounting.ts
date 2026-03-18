import { request } from "./client";

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

export const accounting = {
    journal: {
        list: () => request<JournalEntry[]>("/api/v1/accounting/journal"),
        create: (data: Partial<JournalEntry>) => request<JournalEntry>("/api/v1/accounting/journal", { method: "POST", body: JSON.stringify(data) }),
    },
    assets: {
        list: () => request<FixedAsset[]>("/api/v1/accounting/assets"),
        create: (data: Partial<FixedAsset>) => request<FixedAsset>("/api/v1/accounting/assets", { method: "POST", body: JSON.stringify(data) }),
        update: (id: string, data: Partial<FixedAsset>) => request<FixedAsset>(`/api/v1/accounting/assets/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
        delete: (id: string) => request(`/api/v1/accounting/assets/${id}`, { method: "DELETE" }),
    },
};
