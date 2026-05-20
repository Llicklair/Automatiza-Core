/**
 * AEAT — custodia de certificado digital + presentación electrónica de modelos.
 * Estado: Fase C (preview). Por defecto se usa dry_run=true.
 */
import { request, requestUpload } from "./client";

export interface AeatCertificate {
    id: string;
    label: string;
    subject_cn: string | null;
    issuer_cn: string | null;
    valid_from: string | null;
    valid_until: string | null;
    serial_number: string | null;
    sha256_fingerprint: string | null;
    status: "active" | "revoked";
    uploaded_at: string | null;
    revoked_at: string | null;
    notes: string | null;
    is_expired: boolean;
}

export type AeatPresentationStatus =
    | "pending" | "signed" | "submitted" | "accepted" | "rejected" | "error";

export interface AeatPresentation {
    id: string;
    model_code: string;
    year: number;
    period: string;
    environment: "preproduccion" | "produccion";
    status: AeatPresentationStatus;
    csv_justificante: string | null;
    error_code: string | null;
    error_message: string | null;
    submitted_at: string | null;
    accepted_at: string | null;
    created_at: string | null;
}

export const aeat = {
    certificate: {
        get: () => request<{ active: AeatCertificate | null }>("/api/v1/aeat/certificate"),
        upload: (file: File, password: string, label?: string, notes?: string) => {
            const fd = new FormData();
            fd.append("file", file);
            fd.append("password", password);
            if (label) fd.append("label", label);
            if (notes) fd.append("notes", notes);
            return requestUpload<AeatCertificate>("/api/v1/aeat/certificate/upload", fd);
        },
        revoke: (id: string) =>
            request<AeatCertificate>(`/api/v1/aeat/certificate/${id}`, { method: "DELETE" }),
    },
    presentations: {
        list: (limit = 50) =>
            request<{ items: AeatPresentation[] }>(`/api/v1/aeat/presentations?limit=${limit}`),
        create303FromQuarter: (quarter: number, year: number, environment: "preproduccion" | "produccion" = "preproduccion") =>
            request<AeatPresentation>(
                `/api/v1/aeat/presentations/303-from-quarter?quarter=${quarter}&year=${year}&environment=${environment}`,
                { method: "POST" },
            ),
        submit: (id: string, dryRun = true) =>
            request<AeatPresentation>(
                `/api/v1/aeat/presentations/${id}/submit?dry_run=${dryRun}`,
                { method: "POST" },
            ),
    },
};
