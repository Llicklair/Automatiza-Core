import { request, requestUpload } from "./client";

export interface LlmProviderEntry {
    model: string;
    enabled: boolean;
    has_key: boolean;
}

export interface LlmConfigResponse {
    active_llm_provider: string;
    active_embeddings_provider: string;
    providers: Record<string, LlmProviderEntry>;
    // BYOK: señal autoritativa del backend de si la IA está lista para usarse,
    // y un motivo accionable. Opcionales para compatibilidad con respuestas viejas.
    ai_ready?: boolean;
    ai_reason?: string;
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

export interface ClaudeCodeSetupResponse {
    status: "ready" | "needs_auth" | "installed" | "error";
    version?: string;
    message: string;
}

export interface CertificateStatus {
    has_certificate: boolean;
    cert_subject?: string;
    cert_expires_at?: string;
}

export interface LogoStatus {
    has_logo: boolean;
    logo_path?: string;
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
    setupClaudeCode: () =>
        request<ClaudeCodeSetupResponse>("/api/v1/tenant/claude-code-setup", {
            method: "POST",
        }),
    loginClaudeCode: () =>
        request<ClaudeCodeSetupResponse>("/api/v1/tenant/claude-code-login", {
            method: "POST",
        }),
    logoutClaudeCode: () =>
        request<ClaudeCodeSetupResponse>("/api/v1/tenant/claude-code-logout", {
            method: "POST",
        }),
    certificate: {
        status: () => request<CertificateStatus>("/api/v1/tenant/certificate"),
        upload: (file: File, password: string) => {
            const fd = new FormData();
            fd.append("file", file);
            fd.append("password", password);
            return requestUpload<{ message: string; cert_subject: string; cert_expires_at: string }>(
                "/api/v1/tenant/certificate", fd
            );
        },
        delete: () => request<void>("/api/v1/tenant/certificate", { method: "DELETE" }),
    },
    logo: {
        status: () => request<LogoStatus>("/api/v1/tenant/logo"),
        upload: (file: File) => {
            const fd = new FormData();
            fd.append("file", file);
            return requestUpload<{ message: string; logo_path: string }>(
                "/api/v1/tenant/logo", fd
            );
        },
        delete: () => request<void>("/api/v1/tenant/logo", { method: "DELETE" }),
    },
};
