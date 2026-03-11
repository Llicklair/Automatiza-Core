import { create } from "zustand";

export type ToastType = "success" | "error" | "info" | "warning";

export interface Toast {
    id: string;
    message: string;
    type: ToastType;
}

interface ToastStore {
    toasts: Toast[];
    show: (message: string, type?: ToastType) => void;
    success: (message: string) => void;
    error: (message: string) => void;
    info: (message: string) => void;
    warning: (message: string) => void;
    dismiss: (id: string) => void;
}

export const useToastStore = create<ToastStore>((set) => ({
    toasts: [],

    show: (message, type = "info") => {
        const id = Math.random().toString(36).slice(2);
        set((s) => ({ toasts: [...s.toasts, { id, message, type }] }));
        setTimeout(() => {
            set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }));
        }, 5000);
    },

    success: (message) => useToastStore.getState().show(message, "success"),
    error: (message) => useToastStore.getState().show(message, "error"),
    info: (message) => useToastStore.getState().show(message, "info"),
    warning: (message) => useToastStore.getState().show(message, "warning"),

    dismiss: (id) =>
        set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));

/** Hook shortcut for components */
export const useToast = () => {
    const { success, error, info, warning } = useToastStore();
    return { success, error, info, warning };
};
