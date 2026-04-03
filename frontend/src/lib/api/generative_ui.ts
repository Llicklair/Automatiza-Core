import { request } from "./client";

export interface GenerativeInterface {
    id: string;
    title: string;
    description: string | null;
    prompt: string;
    content_html: string;
    is_pinned: boolean;
    created_at: string;
    updated_at: string;
}

export const generativeUI = {
    generate: (prompt: string) =>
        request<GenerativeInterface>("/api/v1/generative-ui/generate", {
            method: "POST",
            body: JSON.stringify({ prompt }),
        }),

    history: () =>
        request<GenerativeInterface[]>("/api/v1/generative-ui/history"),

    get: (id: string) =>
        request<GenerativeInterface>(`/api/v1/generative-ui/${id}`),

    update: (id: string, data: { title?: string; description?: string }) =>
        request<GenerativeInterface>(`/api/v1/generative-ui/${id}`, {
            method: "PATCH",
            body: JSON.stringify(data),
        }),

    delete: (id: string) =>
        request<void>(`/api/v1/generative-ui/${id}`, { method: "DELETE" }),
};
