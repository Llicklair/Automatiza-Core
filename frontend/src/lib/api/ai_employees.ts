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

export const aiEmployees = {
    list: () =>
        request<AIEmployee[]>("/api/v1/ai-employees"),

    create: (data: { name: string; role_description: string; budget_limit_usd?: number }) =>
        request<AIEmployee>("/api/v1/ai-employees", { method: "POST", body: JSON.stringify(data) }),

    delete: (id: string) =>
        request<void>(`/api/v1/ai-employees/${id}`, { method: "DELETE" }),

    updateStatus: (id: string, status: "idle" | "paused") =>
        request<AIEmployee>(`/api/v1/ai-employees/${id}/status?new_status=${status}`, { method: "PATCH" }),

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
