import { create } from "zustand";

interface ConfirmOptions {
    title?: string;
    message: string;
    confirmLabel?: string;
    confirmVariant?: "danger" | "warning" | "primary";
}

interface ConfirmState {
    open: boolean;
    options: ConfirmOptions | null;
    resolve: ((value: boolean) => void) | null;
    show: (options: ConfirmOptions | string) => Promise<boolean>;
    _confirm: () => void;
    _cancel: () => void;
}

export const useConfirmStore = create<ConfirmState>((set, get) => ({
    open: false,
    options: null,
    resolve: null,

    show: (opts) => {
        const options: ConfirmOptions =
            typeof opts === "string" ? { message: opts } : opts;
        return new Promise<boolean>((resolve) => {
            set({ open: true, options, resolve });
        });
    },

    _confirm: () => {
        get().resolve?.(true);
        set({ open: false, options: null, resolve: null });
    },

    _cancel: () => {
        get().resolve?.(false);
        set({ open: false, options: null, resolve: null });
    },
}));

/** Función de conveniencia usable fuera de componentes React */
export const showConfirm = (opts: ConfirmOptions | string) =>
    useConfirmStore.getState().show(opts);
