import { BASE, getToken, request } from "./client";

export interface SystemInfo {
    status: string;
    version: string;
    checks: Record<string, any>;
}

export interface BackupItem {
    filename: string;
    size_mb: number;
    created_at: string;
    age_hours: number;
}

export interface RunBackupResult {
    created: string | null;
    rotated: number;
    status: string;
}

export interface RestoreResult {
    status: string;
    error: string | null;
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

    listBackups: (): Promise<BackupItem[]> =>
        request<BackupItem[]>("/api/v1/system/backups"),

    runBackup: (): Promise<RunBackupResult> =>
        request<RunBackupResult>("/api/v1/system/backups", { method: "POST" }),

    restoreBackup: (filename: string): Promise<RestoreResult> =>
        request<RestoreResult>(
            `/api/v1/system/backups/${encodeURIComponent(filename)}/restore`,
            { method: "POST" },
        ),

    deleteBackup: (filename: string): Promise<void> =>
        request<void>(
            `/api/v1/system/backups/${encodeURIComponent(filename)}`,
            { method: "DELETE" },
        ),

    downloadBackup: async (filename: string): Promise<void> => {
        const token = getToken();
        const url = `${BASE}/api/v1/system/backups/${encodeURIComponent(filename)}/download`;
        const res = await fetch(url, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!res.ok) throw new Error(await res.text());
        const blob = await res.blob();
        const objectUrl = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = objectUrl;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(objectUrl);
    },
};
