import { request } from "./client";

export interface Project {
    id: string;
    tenant_id: string;
    client_id: string | null;
    name: string;
    description: string | null;
    budget: number;
    status: string;
    start_date: string | null;
    due_date: string | null;
    created_at: string;
}

export interface ProjectTask {
    id: string;
    tenant_id: string;
    project_id: string;
    assignee_id: string | null;
    title: string;
    description: string | null;
    status: 'todo' | 'in_progress' | 'done';
    start_date: string | null;
    due_date: string | null;
    created_at: string;
    project?: Project;
}

export const projects = {
    list: () => request<Project[]>("/api/v1/projects"),
    create: (data: Partial<Project>) => request<Project>("/api/v1/projects", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: Partial<Project>) => request<Project>(`/api/v1/projects/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    delete: (id: string) => request<void>(`/api/v1/projects/${id}`, { method: "DELETE" }),
    tasks: {
        list: (params?: { project_id?: string }) => {
            const q = params?.project_id ? `?project_id=${params.project_id}` : "";
            return request<ProjectTask[]>(`/api/v1/projects/tasks${q}`);
        },
        create: (data: Partial<ProjectTask>) => request<ProjectTask>("/api/v1/projects/tasks", { method: "POST", body: JSON.stringify(data) }),
        update: (id: string, data: Partial<ProjectTask>) => request<ProjectTask>(`/api/v1/projects/tasks/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
        delete: (id: string) => request<void>(`/api/v1/projects/tasks/${id}`, { method: "DELETE" }),
    }
};
