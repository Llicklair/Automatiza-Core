import { getToken, BASE } from "./client";

export const admin = {
    downloadBackup: async () => {
        const token = getToken();
        const res = await fetch(`${BASE}/api/v1/admin/backup`, {
            headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error(await res.text());
        const blob = await res.blob();
        const cd = res.headers.get("Content-Disposition") ?? "";
        const match = cd.match(/filename="([^"]+)"/);
        const filename = match?.[1] ?? `backup_${Date.now()}.sql`;
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url; a.download = filename; a.click();
        URL.revokeObjectURL(url);
    },
    restoreBackup: async (file: File) => {
        const token = getToken();
        const form = new FormData();
        form.append("file", file);
        const res = await fetch(`${BASE}/api/v1/admin/restore`, {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` },
            body: form,
        });
        if (!res.ok) throw new Error(await res.text());
        return res.json() as Promise<{ ok: boolean; message: string }>;
    },
};
