import { request } from "./client";
import type { Invoice } from "./erp";

export interface BankTransaction {
    id: string;
    date: string;
    description: string;
    amount: number;
    balance: number | null;
    status: string; // unreconciled, reconciled, ignored
    invoice_id: string | null;
}

export const banking = {
    summary: () => request<{ ingresos: number; gastos: number; neto: number; margen: number; is_demo: boolean }>("/api/v1/banking/summary"),
    analytics: () => request<{ cashflow: { month: string, ingresos: number, gastos: number }[], insights: { id: string, type: 'success' | 'warning' | 'info' | 'error', title: string, message: string, action_text: string, action_url: string }[] }>("/api/v1/banking/analytics"),
    transactions: {
        list: () => request<BankTransaction[]>("/api/v1/banking/transactions"),
        sync: () => request<{ message: string; status: string }>("/api/v1/banking/transactions/sync", { method: "POST" }),
        reconcile: (id: string, invoice_id: string) => request<{ message: string; status: string }>(`/api/v1/banking/transactions/${id}/reconcile`, {
            method: "POST",
            body: JSON.stringify({ invoice_id })
        })
    }
};
