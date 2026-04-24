/**
 * API client — Messaging (Telegram, Email).
 */
import { request } from "./client";

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
    },
};
