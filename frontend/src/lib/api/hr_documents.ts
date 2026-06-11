import { request, downloadBlob, fetchBlob } from "./client";

export interface HRDocument {
    id: string;
    doc_type: string;
    title: string;
    employee_name: string;
    content_html: string;
    status: "draft" | "approved";
    doc_number: string | null;
    instructions: string | null;
    created_at: string;
    approved_at: string | null;
}

export interface HRDocumentGeneratePayload {
    doc_type: string;
    employee_name?: string;
    employee_id?: string;
    instructions: string;
}

export const hrDocuments = {
    generate: (data: HRDocumentGeneratePayload) =>
        request<HRDocument>("/api/v1/hr/documents/generate", {
            method: "POST",
            body: JSON.stringify(data),
        }),

    list: (params?: { doc_type?: string; status?: string; limit?: number; offset?: number }) => {
        const qs = new URLSearchParams();
        if (params?.doc_type) qs.set("doc_type", params.doc_type);
        if (params?.status) qs.set("status", params.status);
        if (params?.limit) qs.set("limit", String(params.limit));
        if (params?.offset) qs.set("offset", String(params.offset));
        const query = qs.toString() ? `?${qs}` : "";
        return request<HRDocument[]>(`/api/v1/hr/documents${query}`);
    },

    get: (id: string) =>
        request<HRDocument>(`/api/v1/hr/documents/${id}`),

    /** Descarga el PDF server-side (incluye el folio); también es la base para firmar. */
    downloadPdf: (id: string, filename = "documento.pdf") =>
        downloadBlob(`/api/v1/hr/documents/${id}/pdf`, filename),

    /** Obtiene el PDF como Blob (para firmar: convertir a base64 y enviar a AutoFirma). */
    pdfBlob: (id: string) => fetchBlob(`/api/v1/hr/documents/${id}/pdf`),

    approve: (id: string) =>
        request<{ id: string; status: string; approved_at: string; doc_number: string | null }>(`/api/v1/hr/documents/${id}/approve`, { method: "POST" }),

    delete: (id: string) =>
        request<void>(`/api/v1/hr/documents/${id}`, { method: "DELETE" }),
};
