import { create } from "zustand";

interface LicenseStore {
    open: boolean;
    show: () => void;
    hide: () => void;
}

export const useLicenseStore = create<LicenseStore>((set) => ({
    open: false,
    show: () => set({ open: true }),
    hide: () => set({ open: false }),
}));
