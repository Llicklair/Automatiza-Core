import { request } from "./client";

export interface EmailTemplate {
    id: string;
    name: string;
    subject: string;
    html_body: string;
    created_at: string;
    updated_at: string;
}

export interface EmailCampaign {
    id: string;
    name: string;
    subject: string;
    html_body: string;
    status: "draft" | "scheduled" | "sending" | "sent" | "failed";
    scheduled_at: string | null;
    sent_at: string | null;
    total_count: number;
    sent_count: number;
    failed_count: number;
    template_id: string | null;
    created_at: string;
}

export interface CampaignCreate {
    name: string;
    subject: string;
    html_body: string;
    template_id?: string;
    recipient_filter?: "all" | "with_email";
    scheduled_at?: string;
}

export interface TemplateCreate {
    name: string;
    subject: string;
    html_body: string;
}

export const emailMarketingApi = {
    templates: {
        list: () => request<EmailTemplate[]>("/api/v1/email-marketing/templates"),
        create: (data: TemplateCreate) =>
            request<EmailTemplate>("/api/v1/email-marketing/templates", {
                method: "POST",
                body: JSON.stringify(data),
            }),
        update: (id: string, data: Partial<TemplateCreate>) =>
            request<EmailTemplate>(`/api/v1/email-marketing/templates/${id}`, {
                method: "PUT",
                body: JSON.stringify(data),
            }),
        delete: (id: string) =>
            request<void>(`/api/v1/email-marketing/templates/${id}`, { method: "DELETE" }),
    },
    campaigns: {
        list: () => request<EmailCampaign[]>("/api/v1/email-marketing/campaigns"),
        create: (data: CampaignCreate) =>
            request<EmailCampaign>("/api/v1/email-marketing/campaigns", {
                method: "POST",
                body: JSON.stringify(data),
            }),
        update: (id: string, data: Partial<CampaignCreate>) =>
            request<EmailCampaign>(`/api/v1/email-marketing/campaigns/${id}`, {
                method: "PUT",
                body: JSON.stringify(data),
            }),
        delete: (id: string) =>
            request<void>(`/api/v1/email-marketing/campaigns/${id}`, { method: "DELETE" }),
        send: (id: string) =>
            request<{ queued: number }>(`/api/v1/email-marketing/campaigns/${id}/send`, { method: "POST" }),
        previewCount: () =>
            request<{ count: number }>("/api/v1/email-marketing/recipients/count"),
    },
};
