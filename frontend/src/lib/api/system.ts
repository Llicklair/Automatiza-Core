import { BASE, getToken } from "./client";

export interface SystemInfo {
    status: string;
    version: string;
    checks: Record<string, any>;
}

export interface UpdateCheckResult {
    current_version: string;
    latest_version: string;
    update_available: boolean;
    changelog?: string;
    download_url?: string;
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

    checkUpdate: async (): Promise<UpdateCheckResult> => {
        const token = getToken();
        const res = await fetch(`${BASE}/api/v1/system/check-update`, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!res.ok) throw new Error("No se pudo verificar actualizaciones");
        return res.json();
    },
};
