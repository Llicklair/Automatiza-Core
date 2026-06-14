"use client";
import { useSyncExternalStore } from "react";
import { getToken } from "@/lib/api/client";

function computeRole(): string | null {
    try {
        const token = getToken();
        if (!token) return null;
        const payload = JSON.parse(atob(token.split(".")[1]));
        return payload.role ?? null;
    } catch {
        return null;
    }
}

// El rol vive en el token (localStorage), un store externo a React: no cambia
// sin recarga, así que basta un subscribe no-op. getServerSnapshot devuelve
// null para no romper la hidratación (el servidor no ve el token).
const subscribe = () => () => {};

export function useUserRole(): string | null {
    return useSyncExternalStore(subscribe, computeRole, () => null);
}
