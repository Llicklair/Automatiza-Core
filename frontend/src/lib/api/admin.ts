import { fetchBlob, requestUpload } from "./client";

export const admin = {
    downloadBackup: async () => {
        const blob = await fetchBlob("/api/v1/admin/backup");
        // Sin Content-Disposition accesible vía blob helper: usar nombre por defecto.
        const filename = `backup_${Date.now()}.sql`;
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
