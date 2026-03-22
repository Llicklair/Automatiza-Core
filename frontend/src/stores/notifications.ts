import { create } from "zustand";

export type NotifType = "success" | "error" | "info" | "warning";

export interface Notification {
    id: string;
    message: string;
    type: NotifType;
    timestamp: number;
    read: boolean;
}

interface NotificationStore {
    items: Notification[];
    /** Incremented when pages should refetch data (soft refresh) */
    refreshKey: number;
    unreadCount: number;

    push: (message: string, type?: NotifType) => void;
    markAllRead: () => void;
    clear: () => void;
    /** Signal pages to refetch their data */
    triggerRefresh: () => void;
}

const MAX_NOTIFICATIONS = 50;

export const useNotificationStore = create<NotificationStore>((set, get) => ({
    items: [],
    refreshKey: 0,
    unreadCount: 0,

    push: (message, type = "info") => {
        const item: Notification = {
            id: Math.random().toString(36).slice(2),
            message,
            type,
            timestamp: Date.now(),
            read: false,
        };
        set((s) => ({
            items: [item, ...s.items].slice(0, MAX_NOTIFICATIONS),
            unreadCount: s.unreadCount + 1,
        }));
    },

    markAllRead: () =>
        set((s) => ({
            items: s.items.map((n) => ({ ...n, read: true })),
            unreadCount: 0,
        })),

    clear: () => set({ items: [], unreadCount: 0 }),

    triggerRefresh: () => set((s) => ({ refreshKey: s.refreshKey + 1 })),
}));
