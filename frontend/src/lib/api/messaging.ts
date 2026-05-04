/**
 * API client — Messaging (Telegram, Email, Drive).
 */
import { request } from "./client";
import type { Document } from "./documents";

export interface TelegramConnectResponse {
    link_url: string;
    link_token: string;
    bot_username: string | null;
}

export interface TelegramStatus {
    connected: boolean;
    chat_id: number | null;
    username: string | null;
}

export interface EmailProviders {
    gmail: boolean;
    outlook: boolean;
    smtp: boolean;
}

export interface EmailStatus {
    configured: boolean;
    providers: EmailProviders;
}

export interface EmailSendResult {
    result: string;
}

export interface EmailInstructResult {
    success: boolean;
    action: string;
    messages: unknown[];
    error: string | null;
}

export interface InboxMessage {
    id: string;
    from: string;
    subject: string;
    date: string;
    snippet: string;
    unread: boolean;
}

export interface InboxResponse {
    provider: "gmail" | "outlook" | null;
    messages: InboxMessage[];
}

export interface EmailDetail {
    provider: "gmail" | "outlook";
    id: string;
    from: string;
    to: string;
    subject: string;
    date: string;
    body: string;
}

export interface DriveFile {
    id: string;
    name: string;
    mime_type: string;
    size: number | null;
    modified: string;
    is_folder: boolean;
}

export const messaging = {
    telegram: {
        connect: () =>
            request<TelegramConnectResponse>("/api/v1/messaging/telegram/connect", { method: "POST" }),
        disconnect: () =>
            request<{ status: string }>("/api/v1/messaging/telegram/disconnect", { method: "DELETE" }),
        status: () =>
            request<TelegramStatus>("/api/v1/messaging/telegram/status"),
        setupWebhook: () =>
            request<{ status: string; result: unknown }>("/api/v1/messaging/telegram/setup-webhook", { method: "POST" }),
    },
    email: {
        status: () =>
            request<EmailStatus>("/api/v1/messaging/email/status"),
        send: (to: string, subject: string, body: string, attachmentIds?: string[]) =>
            request<EmailSendResult>("/api/v1/messaging/email/send", {
                method: "POST",
                body: JSON.stringify({ to, subject, body, attachment_ids: attachmentIds }),
            }),
        instruct: (message: string, taskId?: string) =>
            request<EmailInstructResult>("/api/v1/messaging/email/instruct", {
                method: "POST",
                body: JSON.stringify({ message, task_id: taskId }),
            }),
        inbox: (limit = 20) =>
            request<InboxResponse>(`/api/v1/messaging/email/inbox?limit=${limit}`),
        getMessage: (id: string) =>
            request<EmailDetail>(`/api/v1/messaging/email/messages/${encodeURIComponent(id)}`),
    },
    drive: {
        list: (folder = "root", q = "") => {
            const params = new URLSearchParams({ folder });
            if (q) params.set("q", q);
            return request<{ files: DriveFile[] }>(`/api/v1/messaging/drive/files?${params}`);
        },
        attachAsDocument: (fileId: string) =>
            request<Document>(`/api/v1/messaging/drive/attach/${encodeURIComponent(fileId)}`, {
                method: "POST",
            }),
    },
};
