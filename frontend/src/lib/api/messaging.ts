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
            request<TelegramConnectResponse>("/messaging/telegram/connect", { method: "POST" }),
        disconnect: () =>
            request<{ status: string }>("/messaging/telegram/disconnect", { method: "DELETE" }),
        status: () =>
            request<TelegramStatus>("/messaging/telegram/status"),
        setupWebhook: () =>
            request<{ status: string; result: unknown }>("/messaging/telegram/setup-webhook", { method: "POST" }),
    },
};
