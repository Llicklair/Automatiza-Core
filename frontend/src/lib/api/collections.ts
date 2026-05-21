/**
 * Inteligencia de cobros (F3.9) — ranking de morosidad + recordatorios.
 */
import { request } from "./client";

export type RiskLevel = "low" | "medium" | "high";

export interface ClientRiskScore {
    client_id: string;
    client_name: string;
    nif: string | null;
    total_invoices: number;
    paid_count: number;
    unpaid_count: number;
    overdue_count: number;
    overdue_amount: number;
    max_days_overdue: number;
    days_avg_to_pay: number | null;
    ratio_paid_on_time: number | null;
    risk_level: RiskLevel;
    risk_score: number;
    drivers: string[];
}

export interface CollectionsRiskResponse {
    count: number;
    high_risk_count: number;
    total_outstanding: number;
    clients: ClientRiskScore[];
}

export type ReminderStepKind =
    | "friendly_pre"
    | "reminder_due"
    | "formal_d15"
    | "formal_d30";

export interface ReminderStep {
    invoice_id: string;
    invoice_number: string | null;
    client_id: string | null;
    client_name: string | null;
    client_email: string | null;
    amount: number;
    due_date: string;
    step: ReminderStepKind;
    fire_date: string;
    days_overdue: number;
    subject: string;
    body: string;
    interest_amount: number;
}

export interface DueRemindersResponse {
    fire_date: string;
    count: number;
    steps: ReminderStep[];
}

export const collections = {
    /** Ranking de clientes por riesgo de cobro (heurística). */
    risk: (onlyWithOutstanding = true) =>
        request<CollectionsRiskResponse>(
            `/api/v1/collections/risk?only_with_outstanding=${onlyWithOutstanding}`,
        ),
    /** Lista de recordatorios planificados para hoy (o `fireDate`). */
    dueReminders: (fireDate?: string) => {
        const qs = fireDate ? `?fire_date=${fireDate}` : "";
        return request<DueRemindersResponse>(`/api/v1/collections/due-reminders${qs}`);
    },
};
