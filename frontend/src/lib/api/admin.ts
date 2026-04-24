import { getToken, BASE, requestUpload } from "./client";

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
    restoreBackup: (file: File): Promise<{ ok: boolean; message: string }> => {
        const form = new FormData();
        form.append("file", file);
        return requestUpload("/api/v1/admin/restore", form);
    },
};
