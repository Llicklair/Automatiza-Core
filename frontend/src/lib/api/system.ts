import { BASE, getToken } from "./client";

export interface SystemInfo {
    status: string;
    version: string;
    checks: Record<string, any>;
}

export const system = {
    health: async (): Promise<SystemInfo> => {
        const token = getToken();
        const res = await fetch(`${BASE}/health`, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!res.ok) throw new Error("No se pudo conectar al servidor");
        return res.json();
    },
};
