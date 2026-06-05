import { FileText, FileImage, FileArchive } from "lucide-react";
import { BASE, getToken } from "@/lib/api/client";

// Reutiliza la BASE derivada del host (client.ts) en vez de fijar 127.0.0.1,
// para que Documentos funcione también vía LAN (móvil del empleado). El override
// por env se respeta si alguna vez se define.
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? BASE;

export function authHeaders() {
    const token = getToken() ?? "";
    return { Authorization: `Bearer ${token}` };
}

export const STATUS_STYLE: Record<string, { label: string; color: string }> = {
    uploaded: { label: "Subido", color: "text-blue-400 bg-blue-500/10" },
    processing: { label: "Procesando", color: "text-amber-400 bg-amber-500/10" },
    processed: { label: "Procesado", color: "text-emerald-400 bg-emerald-500/10" },
    ready: { label: "Listo", color: "text-emerald-400 bg-emerald-500/10" },
    completed: { label: "Completado", color: "text-emerald-400 bg-emerald-500/10" },
    failed: { label: "Error", color: "text-red-400 bg-red-500/10" },
};

export function fileIcon(type: string | null) {
    if (!type) return FileText;
    if (type.startsWith("image/")) return FileImage;
    if (type.includes("zip") || type.includes("rar")) return FileArchive;
    return FileText;
}

export function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
