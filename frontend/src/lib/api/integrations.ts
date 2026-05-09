import { request } from "./client";

export interface IntegrationStatus {
    integration_type: string;
    is_active: boolean;
    last_sync_at?: string;
}

export interface GmailMessage {
    id: string;
    thread_id: string;
    from: string;
    to: string;
    subject: string;
    date: string;
    snippet: string;
    label_ids: string[];
}

export interface DriveFile {
    id: string;
    name: string;
    mimeType: string;
    size?: string;
    modifiedTime: string;
    webViewLink?: string;
}

export interface OutlookMessage {
    id: string;
    subject: string;
    from: string;
    from_name: string;
    to: string;
    date: string;
    snippet: string;
    is_read: boolean;
}

export interface OneDriveFile {
    id: string;
    name: string;
    mimeType?: string;
    size?: number;
    lastModifiedDateTime?: string;
    webUrl?: string;
}

export interface EmailConnectInput {
    email_address: string;
    password: string;
    provider: string;
    imap_host?: string;
    imap_port?: number;
    smtp_host?: string;
    smtp_port?: number;
}

export interface EmailConnectStatus {
    connected: boolean;
    provider?: string;
    email_address?: string;
}

export const integrations = {
    list: () => request<IntegrationStatus[]>("/api/v1/integrations/"),
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
    gmailStatus: () =>
        request<{ connected: boolean }>("/api/v1/integrations/gmail/status"),
    gdriveStatus: () =>
        request<{ connected: boolean }>("/api/v1/integrations/gdrive/status"),
    gmailRecent: () =>
        request<GmailMessage[]>("/api/v1/integrations/gmail/recent"),
    gdriveRecent: () =>
        request<DriveFile[]>("/api/v1/integrations/gdrive/recent"),
    outlookStatus: () =>
        request<{ connected: boolean }>("/api/v1/integrations/outlook/status"),
    onedriveStatus: () =>
        request<{ connected: boolean }>("/api/v1/integrations/onedrive/status"),
    outlookRecent: () =>
        request<OutlookMessage[]>("/api/v1/integrations/outlook/recent"),
    onedriveRecent: () =>
        request<OneDriveFile[]>("/api/v1/integrations/onedrive/recent"),
    emailStatus: () =>
        request<EmailConnectStatus>("/api/v1/integrations/email/status"),
    connectEmail: (payload: EmailConnectInput) =>
        request<{ status: string }>("/api/v1/integrations/email/connect", {
            method: "POST", body: JSON.stringify(payload),
        }),
    disconnectEmail: () =>
        request("/api/v1/integrations/email/disconnect", { method: "DELETE" }),
};
