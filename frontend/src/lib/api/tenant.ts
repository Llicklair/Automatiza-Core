import { request } from "./client";

export interface LlmProviderEntry {
    model: string;
    enabled: boolean;
    has_key: boolean;
}

export interface LlmConfigResponse {
    active_llm_provider: string;
    active_embeddings_provider: string;
    providers: Record<string, LlmProviderEntry>;
}

export interface LlmProviderConfigUpdate {
    api_key?: string;
    model?: string;
    enabled: boolean;
}

export interface LlmConfigUpdate {
    active_llm_provider?: string;
    active_embeddings_provider?: string;
    providers?: Record<string, LlmProviderConfigUpdate>;
}

export const tenant = {
    me: () => request<{ id: string; name: string; nif: string; address: string | null; phone: string | null; contact_email: string | null }>("/api/v1/tenant/me"),
    updateMe: (data: { name?: string; nif?: string; address?: string | null; phone?: string | null; contact_email?: string | null }) =>
        request<{ id: string; name: string; nif: string; address: string | null; phone: string | null; contact_email: string | null }>("/api/v1/tenant/me", {
            method: "PATCH",
            body: JSON.stringify(data),
        }),
    getLlmConfig: () => request<LlmConfigResponse>("/api/v1/tenant/llm-config"),
    updateLlmConfig: (data: LlmConfigUpdate) =>
        request<LlmConfigResponse>("/api/v1/tenant/llm-config", {
            method: "PUT",
            body: JSON.stringify(data),
        }),
};
