import { request, requestUpload, downloadBlob, fetchBlob } from "./client";

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
    upload: (file: File, category?: string): Promise<Document> => {
        const form = new FormData();
        form.append("file", file);
        if (category) form.append("category", category);
        return requestUpload<Document>("/api/v1/documents/upload", form);
    },
    importDB: (files: File[]): Promise<{ document_id: string; file_name: string; rows_detected: number; columns: string[]; category: string; task_id: string | null; message: string }[]> => {
        const form = new FormData();
        for (const f of files) form.append("files", f);
        return requestUpload("/api/v1/documents/import-db", form);
    },
    scan: (files: File[]): Promise<{ document: Document; auto_category: string; message: string }[]> => {
        const form = new FormData();
        for (const f of files) form.append("files", f);
        return requestUpload("/api/v1/documents/scan", form);
    },
    download: (id: string, filename: string) => downloadBlob(`/api/v1/documents/${id}/download`, filename),
    previewBlob: (id: string) => fetchBlob(`/api/v1/documents/${id}/download`),
    delete: (id: string) => request(`/api/v1/documents/${id}`, { method: "DELETE" }),
    exportZip: () => downloadBlob("/api/v1/documents/export", "documentos_backup.zip"),
    contractTemplates: {
        list: (): Promise<ContractTemplate[]> =>
            request<ContractTemplate[]>("/api/v1/documents/contract-templates"),
        upload: (file: File): Promise<ContractTemplate> => {
            const form = new FormData();
            form.append("file", file);
            return requestUpload<ContractTemplate>("/api/v1/documents/contract-templates/upload", form);
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
        generate: (templateId: string, entityType: "client" | "employee", entityId: string): Promise<Blob> => {
            const params = new URLSearchParams({ entity_type: entityType, entity_id: entityId });
            return fetchBlob(`/api/v1/documents/contract-templates/${templateId}/generate?${params}`, { method: "POST" });
        },
    },
    uploadBulk: (file: File, category?: string): Promise<Document[]> => {
        const form = new FormData();
        form.append("file", file);
        if (category) form.append("category", category);
        return requestUpload<Document[]>("/api/v1/documents/bulk", form);
    },
};
