import { request } from "./client";

export interface IntegrationStatus {
    integration_type: string;
    is_active: boolean;
    last_sync_at?: string;
}

export const integrations = {
    list: () => request<IntegrationStatus[]>("/api/v1/integrations/"),
    connectHolded: (apiKey: string) =>
        request<{ status: string }>("/api/v1/integrations/holded/connect", {
            method: "POST", body: JSON.stringify({ api_key: apiKey }),
        }),
    disconnectHolded: () =>
        request("/api/v1/integrations/holded/disconnect", { method: "DELETE" }),
    connectPsd2: (secretId: string, secretKey: string) =>
        request<{ status: string }>("/api/v1/integrations/psd2/connect", {
            method: "POST", body: JSON.stringify({ secret_id: secretId, secret_key: secretKey }),
        }),
    disconnectPsd2: () =>
        request("/api/v1/integrations/psd2/disconnect", { method: "DELETE" }),
    oauthUrl: (provider: "google" | "microsoft") =>
        request<{ auth_url: string }>(`/api/v1/integrations/${provider}/auth-url`),
    disconnect: (type: string) =>
        request(`/api/v1/integrations/${type}/disconnect`, { method: "DELETE" }),
};
