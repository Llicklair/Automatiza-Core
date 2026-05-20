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

export interface InvoiceSuggestion {
    id: string;
    invoice_number: string | null;
    amount_total: number;
    client_name: string | null;
    status: string;
    date: string | null;
    /** 0-100 — confianza del matching (importe + fecha + cliente + nº factura). */
    score?: number;
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
    },
};
