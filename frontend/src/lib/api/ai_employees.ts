import { request } from "./client";

export interface AIEmployee {
    id: string;
    name: string;
    role: string;
    domain: string;
    status: "idle" | "working" | "paused" | "blocked" | "pending_setup";
    is_builtin: boolean;
    budget_limit_usd: number | null;
    doc_folder: string | null;
    icon: string | null;
    avatar_color: string | null;
}

export interface ActivityEntry {
    id: string;
    employee_id: string | null;
    category: string;
    icon: string;
    message: string;
    metadata: Record<string, any> | null;
    created_at: string;
}

export interface AvailableSkill {
    module: string;
    label: string;
}

export interface UsageEntry {
    id: string;
    task_id: string | null;
    provider: string | null;
    tokens_in: number;
    tokens_out: number;
    cost_usd: number;
    created_at: string;
}

export interface EmployeeUsage {
    employee_id: string;
    total_calls: number;
    total_tokens_in: number;
    total_tokens_out: number;
    total_cost_usd: number;
    entries: UsageEntry[];
}

export const aiEmployees = {
    list: () =>
        request<AIEmployee[]>("/api/v1/ai-employees"),

    create: (data: {
        name: string;
        role_description: string;
        budget_limit_usd?: number;
        scope?: Record<string, any> | null;
        memory_enabled?: boolean;
        knowledge_enabled?: boolean;
        workflows?: Array<Record<string, any>> | null;
    }) =>
        request<AIEmployee>("/api/v1/ai-employees", { method: "POST", body: JSON.stringify(data) }),

    delete: (id: string) =>
        request<void>(`/api/v1/ai-employees/${id}`, { method: "DELETE" }),

    updateStatus: (id: string, status: "idle" | "paused") =>
        request<AIEmployee>(`/api/v1/ai-employees/${id}/status?new_status=${status}`, { method: "PATCH" }),

    /** Ajusta el tope de gasto mensual (USD). `null` = sin límite. */
    updateBudget: (id: string, budget_limit_usd: number | null) =>
        request<AIEmployee>(`/api/v1/ai-employees/${id}/budget`, {
            method: "PATCH",
            body: JSON.stringify({ budget_limit_usd }),
        }),

    updateIcon: (id: string, icon: string) =>
        request<AIEmployee>(`/api/v1/ai-employees/${id}/icon`, { method: "PATCH", body: JSON.stringify({ icon }) }),

    updateAppearance: (id: string, data: { icon?: string; avatar_color?: string }) =>
        request<AIEmployee>(`/api/v1/ai-employees/${id}/appearance`, { method: "PATCH", body: JSON.stringify(data) }),

    instruct: (id: string, message: string) =>
        request<{ task_id: string; status: string; employee: string }>(
            `/api/v1/ai-employees/${id}/instruct`,
            { method: "POST", body: JSON.stringify({ message }) }
        ),

    availableSkills: () =>
        request<AvailableSkill[]>("/api/v1/ai-employees/available-skills"),

    seed: () =>
        request<{ created: string[]; message: string }>("/api/v1/ai-employees/seed", { method: "POST" }),

    usage: (id: string, params?: { limit?: number; offset?: number }) => {
        const qs = new URLSearchParams();
        if (params?.limit) qs.set("limit", String(params.limit));
        if (params?.offset) qs.set("offset", String(params.offset));
        const query = qs.toString() ? `?${qs}` : "";
        return request<EmployeeUsage>(`/api/v1/ai-employees/${id}/usage${query}`);
    },

    activityFeed: (params?: { employee_id?: string; category?: string; limit?: number; offset?: number }) => {
        const qs = new URLSearchParams();
        if (params?.employee_id) qs.set("employee_id", params.employee_id);
        if (params?.category) qs.set("category", params.category);
        if (params?.limit) qs.set("limit", String(params.limit));
        if (params?.offset) qs.set("offset", String(params.offset));
        const query = qs.toString() ? `?${qs}` : "";
        return request<ActivityEntry[]>(`/api/v1/activity-feed${query}`);
    },
};
