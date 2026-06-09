import { create } from "zustand";

interface LicenseStore {
    open: boolean;
    plan: string;
    show: () => void;
    hide: () => void;
    setPlan: (plan: string) => void;
}

export const useLicenseStore = create<LicenseStore>((set) => ({
    open: false,
    plan: "",
    show: () => set({ open: true }),
    hide: () => set({ open: false }),
    setPlan: (plan) => set({ plan }),
}));
