import { request } from "./client";

export interface AlertEntry {
    id: string;
    alert_type: "overdue_invoice" | "due_soon_invoice" | "low_stock" | "pending_payroll";
    entity_id: string;
    entity_label: string;
    severity: "info" | "warning" | "error";
    sent_at: string;
}

export const alertsApi = {
    list: (hours = 48) => request<AlertEntry[]>(`/api/v1/alerts?hours=${hours}`),
    check: () => request<{ new_alerts: number; message: string }>("/api/v1/alerts/check", { method: "POST" }),
};
