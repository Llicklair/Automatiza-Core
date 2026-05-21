import { request } from "./client";

export interface BankTransaction {
    id: string;
    date: string;
    description: string;
    amount: number;
    balance: number | null;
    status: string; // unreconciled, reconciled, ignored
    invoice_id: string | null;
}

/** Razón legible por la que un par tx↔factura ha sumado puntos (F2.6). */
export interface MatchReason {
    code:
        | "amount_exact"
        | "date_within_15d"
        | "date_within_45d"
        | "client_name_match"
        | "client_token_match"
        | "invoice_number_match"
        | string;
    label: string;
    points: number;
}

export interface InvoiceSuggestion {
    id: string;
    invoice_number: string | null;
    amount_total: number;
    client_name: string | null;
    status: string;
    date: string | null;
    /** 0-100 — confianza del matching (importe + fecha + cliente + nº factura). */
    score?: number;
    /** Desglose de las razones detrás del score (F2.6 — explicabilidad). */
    reasons?: MatchReason[];
}

export interface ReconciliationSuggestion {
    tx: { id: string; date: string; description: string; amount: number };
    suggestions: InvoiceSuggestion[];
}

export const banking = {
    summary: () => request<{ ingresos: number; gastos: number; neto: number; margen: number; is_demo: boolean }>("/api/v1/banking/summary"),
    analytics: () => request<{ cashflow: { month: string, ingresos: number, gastos: number }[], insights: { id: string, type: 'success' | 'warning' | 'info' | 'error', title: string, message: string, action_text: string, action_url: string }[] }>("/api/v1/banking/analytics"),
    transactions: {
        list: () => request<BankTransaction[]>("/api/v1/banking/transactions"),
        sync: () => request<{ message: string; status: string }>("/api/v1/banking/transactions/sync", { method: "POST" }),
        reconcile: (id: string, invoice_id: string) => request<{ message: string; status: string }>(`/api/v1/banking/transactions/${id}/reconcile`, {
            method: "POST",
            body: JSON.stringify({ invoice_id }),
        }),
        ignore: (id: string) => request<{ message: string; status: string }>(`/api/v1/banking/transactions/${id}/ignore`, { method: "POST" }),
        unreconcile: (id: string) => request<{ message: string; status: string }>(`/api/v1/banking/transactions/${id}/unreconcile`, { method: "POST" }),
    },
    reconciliation: {
        suggestions: () => request<ReconciliationSuggestion[]>("/api/v1/banking/reconciliation/suggestions"),
        autoMatch: () => request<{ matched: number; total: number }>("/api/v1/banking/reconciliation/auto-match", { method: "POST" }),
        /** Marca un par (tx, factura) como rechazado para que no vuelva a sugerirse (F2.6). */
        reject: (transaction_id: string, invoice_id: string, reason?: string) =>
            request<{ rejected: boolean; new: boolean }>("/api/v1/banking/reconciliation/reject", {
                method: "POST",
                body: JSON.stringify({ transaction_id, invoice_id, reason }),
            }),
    },
};
