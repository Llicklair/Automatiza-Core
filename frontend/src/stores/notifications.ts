import { create } from "zustand";
import { api } from "@/lib/api";
import type { PersistentNotification } from "@/lib/api/notifications";

export type NotifType = "success" | "error" | "info" | "warning";

export interface Notification {
    id: string;
    message: string;
    type: NotifType;
    timestamp: number;
    read: boolean;
    /** UI.NOT — true cuando viene de BD (persistente cross-session). */
    persisted?: boolean;
}

interface NotificationStore {
    items: Notification[];
    /** Incremented when pages should refetch data (soft refresh) */
    refreshKey: number;
    unreadCount: number;
    hydrated: boolean;

    push: (message: string, type?: NotifType) => void;
    markAllRead: () => void;
    markOneRead: (id: string) => void;
    clear: () => void;
    /** Signal pages to refetch their data */
    triggerRefresh: () => void;
    /** UI.NOT — carga notificaciones persistidas en BD. */
    hydrate: () => Promise<void>;
}

const MAX_NOTIFICATIONS = 50;

function _persistedToLocal(p: PersistentNotification): Notification {
    return {
        id: p.id,
        message: p.body ? `${p.title} — ${p.body}` : p.title,
        type: p.kind as NotifType,
        timestamp: new Date(p.created_at).getTime(),
        read: p.read_at !== null,
        persisted: true,
    };
}

export const useNotificationStore = create<NotificationStore>((set, get) => ({
    items: [],
    refreshKey: 0,
    unreadCount: 0,
    hydrated: false,

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

    markAllRead: () => {
        // Optimista local + persistir solo las que vinieron de BD.
        set((s) => ({
            items: s.items.map((n) => ({ ...n, read: true })),
            unreadCount: 0,
        }));
        // Best-effort: no bloquea la UI si falla.
        api.notifications.markAllRead().catch(() => { /* silenciado */ });
    },

    markOneRead: (id) => {
        set((s) => {
            const target = s.items.find((n) => n.id === id);
            if (!target || target.read) return s;
            return {
                items: s.items.map((n) => (n.id === id ? { ...n, read: true } : n)),
                unreadCount: Math.max(0, s.unreadCount - 1),
            };
        });
        const target = get().items.find((n) => n.id === id);
        if (target?.persisted) {
            api.notifications.markRead(id).catch(() => { /* silenciado */ });
        }
    },

    clear: () => set({ items: [], unreadCount: 0 }),

    triggerRefresh: () => set((s) => ({ refreshKey: s.refreshKey + 1 })),

    hydrate: async () => {
        if (get().hydrated) return;
        try {
            const res = await api.notifications.list(false, 50);
            const persisted = res.items.map(_persistedToLocal);
            set((s) => {
                // Conservamos items volátiles ya en el store (toasts del WS in-flight)
                // y prepend los persistidos por timestamp desc.
                const volatile = s.items.filter((i) => !i.persisted);
                const merged = [...persisted, ...volatile]
                    .sort((a, b) => b.timestamp - a.timestamp)
                    .slice(0, MAX_NOTIFICATIONS);
                return {
                    items: merged,
                    unreadCount: res.unread_count,
                    hydrated: true,
                };
            });
        } catch {
            // Sin BD disponible: nos quedamos en modo solo-memoria.
            set({ hydrated: true });
        }
    },
}));
