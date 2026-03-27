import { create } from "zustand";

interface NavigationGuardStore {
    blocked: boolean;
    message: string;
    setGuard: (blocked: boolean, message?: string) => void;
}

export const useNavigationGuard = create<NavigationGuardStore>((set) => ({
    blocked: false,
    message: "",
    setGuard: (blocked, message = "") => set({ blocked, message }),
}));
