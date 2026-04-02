import { request, getToken, downloadBlob, BASE } from "./client";

export interface Document {
    id: string;
    file_name: string;
    file_type: string | null;
    file_size: number;
    status: string;
    category: string | null;
    parsed_content: string | null;
    created_at: string;
    processed_at: string | null;
    task_id: string | null;
}

export interface ContractTemplate {
    id: string;
    file_name: string;
    file_size: number;
    file_path: string;
    created_at: string;
}

/** Respuesta de GET .../contract-templates/:id/preview-html (mammoth) */
export interface ContractPreviewHtml {
    html: string;
    /** HTML mammoth sin resaltado — para TipTap */
    html_editable: string;
    variables_detected: string[];
    warnings: string[];
}

export const documents = {
    list: (params?: { category?: string; skip?: number; limit?: number }) => {
        const q = new URLSearchParams(params as Record<string, string>).toString();
        return request<Document[]>(`/api/v1/documents${q ? "?" + q : ""}`);
    },
    upload: async (file: File, category?: string): Promise<Document> => {
        const token = getToken();
        const form = new FormData();
        form.append("file", file);
        if (category) form.append("category", category);

        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;
        const res = await fetch(`${BASE}/api/v1/documents/upload`, {
            method: "POST",
            headers,
            body: form,
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail ?? "Error al subir archivo");
        }
        return res.json();
    },
    importDB: async (files: File[]): Promise<{ document_id: string; file_name: string; rows_detected: number; columns: string[]; category: string; task_id: string | null; message: string }[]> => {
        const token = getToken();
        const form = new FormData();
        for (const f of files) form.append("files", f);

        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;
        const res = await fetch(`${BASE}/api/v1/documents/import-db`, {
            method: "POST",
            headers,
            body: form,
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail ?? "Error al importar base de datos");
        }
        return res.json();
    },
    scan: async (files: File[]): Promise<{ document: Document; auto_category: string; message: string }[]> => {
        const token = getToken();
        const form = new FormData();
        for (const f of files) form.append("files", f);

        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;
        const res = await fetch(`${BASE}/api/v1/documents/scan`, {
            method: "POST",
            headers,
            body: form,
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail ?? "Error al escanear archivos");
        }
        return res.json();
    },
    delete: (id: string) => request(`/api/v1/documents/${id}`, { method: "DELETE" }),
    exportZip: () => downloadBlob("/api/v1/documents/export", "documentos_backup.zip"),
    contractTemplates: {
        list: (): Promise<ContractTemplate[]> =>
            request<ContractTemplate[]>("/api/v1/documents/contract-templates"),
        upload: async (file: File): Promise<ContractTemplate> => {
            const token = getToken();
            const form = new FormData();
            form.append("file", file);
            const headers: Record<string, string> = {};
            if (token) headers["Authorization"] = `Bearer ${token}`;
            const res = await fetch(`${BASE}/api/v1/documents/contract-templates/upload`, {
                method: "POST",
                headers,
                body: form,
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: res.statusText }));
                throw new Error(err.detail ?? "Error al subir plantilla");
            }
            return res.json();
        },
        delete: (id: string) =>
            request(`/api/v1/documents/contract-templates/${id}`, { method: "DELETE" }),
        previewHtml: (templateId: string): Promise<ContractPreviewHtml> =>
            request<ContractPreviewHtml>(
                `/api/v1/documents/contract-templates/${templateId}/preview-html`
            ),
        saveBodyHtml: (templateId: string, html: string): Promise<{ status: string; file_size: number }> =>
            request(`/api/v1/documents/contract-templates/${templateId}/body-html`, {
                method: "PUT",
                body: JSON.stringify({ html }),
            }),
        generate: async (templateId: string, entityType: "client" | "employee", entityId: string): Promise<Blob> => {
            const token = getToken();
            const headers: Record<string, string> = {};
            if (token) headers["Authorization"] = `Bearer ${token}`;
            const params = new URLSearchParams({ entity_type: entityType, entity_id: entityId });
            const res = await fetch(
                `${BASE}/api/v1/documents/contract-templates/${templateId}/generate?${params}`,
                { method: "POST", headers }
            );
            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: res.statusText }));
                throw new Error(err.detail ?? "Error generando contrato");
            }
            return res.blob();
        },
    },
    uploadBulk: async (file: File, category?: string): Promise<Document[]> => {
        const token = getToken();
        const form = new FormData();
        form.append("file", file);
        if (category) form.append("category", category);

        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;
        const res = await fetch(`${BASE}/api/v1/documents/bulk`, {
            method: "POST",
            headers,
            body: form,
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail ?? "Error al subir archivo ZIP");
        }
        return res.json();
    },
};
