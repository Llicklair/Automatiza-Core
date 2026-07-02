import { request } from "./client";

export interface Task {
    id: string;
    tenant_id: string;
    status: string;
    domain: string;
    user_intent: string;
    plan: any[];
    agent_results?: any[];
    /** Salida final agregada (backend Task.output_data) */
    output_data?: unknown;
    current_step: number;
    requires_human_approval: boolean;
    error_message: string | null;
    additional_metadata?: Record<string, unknown> | null;
    created_at: string;
    started_at: string | null;
    completed_at: string | null;
}

export interface AuditEntry {
    id: number;
    task_id: string;
    agent_name: string;
    action_type: string;
    input_data: unknown;
    output_data: unknown;
    status: string;
    error_detail: string | null;
    executed_at: string;
}

export interface Approval {
    id: string;
    task_id: string;
    action_description: string;
    action_payload: unknown;
    risk_level: string;
    expires_at: string;
    status: string;
}

export const tasks = {
    list: (params?: { status?: string; skip?: number; limit?: number }) => {
        const q = new URLSearchParams(params as Record<string, string>).toString();
        return request<Task[]>(`/api/v1/tasks${q ? "?" + q : ""}`);
    },
    create: (domain: string, user_intent: string, additional_metadata?: Record<string, unknown>, parent_task_id?: string) =>
        request<Task>("/api/v1/tasks", {
            method: "POST",
            body: JSON.stringify({
                domain,
                user_intent,
                ...(additional_metadata ? { additional_metadata } : {}),
                ...(parent_task_id ? { parent_task_id } : {}),
            }),
        }),
    get: (id: string) => request<Task>(`/api/v1/tasks/${id}`),
    cancel: (id: string) =>
        request(`/api/v1/tasks/${id}`, { method: "DELETE" }),
    audit: (id: string) => request<AuditEntry[]>(`/api/v1/tasks/${id}/audit`),
    cleanup: () => request<{ deleted: number }>("/api/v1/tasks/cleanup", { method: "DELETE" }),
};

export const TERMINAL_TASK_STATUSES = new Set(["done", "failed", "awaiting_approval"]);

export class TaskTimeoutError extends Error {
    constructor(public taskId: string, timeoutMs: number) {
        super(`Task ${taskId} still running after ${timeoutMs / 1000}s`);
        this.name = "TaskTimeoutError";
    }
}

/**
 * Espera (polling) a que una task alcance estado terminal. Lanza
 * TaskTimeoutError si sigue en curso al agotar el timeout — la task NO se
 * cancela, sigue visible en /mi-equipo?tab=tareas.
 */
export async function waitForTask(
    taskId: string,
    opts: { timeoutMs?: number; intervalMs?: number } = {},
): Promise<Task> {
    const { timeoutMs = 120_000, intervalMs = 2_000 } = opts;
    const start = Date.now();
    let task = await tasks.get(taskId);
    while (!TERMINAL_TASK_STATUSES.has(task.status)) {
        if (Date.now() - start > timeoutMs) throw new TaskTimeoutError(taskId, timeoutMs);
        await new Promise(r => setTimeout(r, intervalMs));
        task = await tasks.get(taskId);
    }
    return task;
}

export const approvals = {
    list: () => request<Approval[]>("/api/v1/approvals"),
    decide: (id: string, approved: boolean, rejection_reason?: string) =>
        request<Approval>(`/api/v1/approvals/${id}/decide`, {
            method: "POST",
            body: JSON.stringify({ approved, rejection_reason }),
        }),
    cleanup: () => request<{ deleted: number }>("/api/v1/approvals/cleanup", { method: "DELETE" }),
};
