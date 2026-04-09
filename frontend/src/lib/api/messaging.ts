/**
 * API client — Messaging (Telegram, WhatsApp).
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
};
