/**
 * UI.NOT — cliente de notificaciones persistentes.
 */
import { request } from "./client";

export interface PersistentNotification {
    id: string;
    kind: "info" | "success" | "warning" | "error";
    title: string;
    body: string | null;
    payload: Record<string, unknown> | null;
    read_at: string | null;
    created_at: string;
}

export interface NotificationListResponse {
    items: PersistentNotification[];
    unread_count: number;
}

export const notificationsApi = {
    list: (onlyUnread = false, limit = 50): Promise<NotificationListResponse> =>
        request<NotificationListResponse>(
            `/api/v1/notifications?only_unread=${onlyUnread}&limit=${limit}`,
        ),

    markRead: (id: string): Promise<{ ok: boolean }> =>
        request<{ ok: boolean }>(`/api/v1/notifications/${id}/read`, {
            method: "PATCH",
        }),

    markAllRead: (): Promise<{ marked_read: number }> =>
        request<{ marked_read: number }>(`/api/v1/notifications/mark-all-read`, {
            method: "POST",
        }),
};
