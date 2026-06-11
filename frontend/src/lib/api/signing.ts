/**
 * Firma electrónica AutoFirma del Estado (F3.11).
 *
 * Flujo desde el frontend:
 *   1. `signing.autofirma.init(...)` → devuelve URI `afirma://`.
 *   2. Disparar la URI con `window.location.href = uri` (o `<a href=...>`).
 *   3. El cliente AutoFirma local se abre con el certificado FNMT del
 *      usuario y firma el documento.
 *   4. AutoFirma POSTea al callback configurado en el backend (no es
 *      necesario hacer nada desde el frontend para ese paso).
 *   5. El frontend hace polling a `signing.autofirma.status(token)` para
 *      saber cuándo el `status` pase a "signed" o "failed".
 */
import { request } from "./client";

export type SignatureFormat = "PAdES" | "XAdES" | "CAdES";

export interface AutoFirmaInitRequest {
    document_b64: string;
    document_id?: string | null;
    signature_format?: SignatureFormat;
    visible_signature?: boolean;
}

export interface AutoFirmaInitResult {
    session_token: string;
    signed_document_id: string;
    autofirma_uri: string;
    original_hash: string;
    signature_format: SignatureFormat;
}

export interface SignedDocumentStatus {
    session_token: string;
    status: "pending" | "signed" | "failed";
    signed_hash: string | null;
}

export const signing = {
    autofirma: {
        init: (req: AutoFirmaInitRequest) =>
            request<AutoFirmaInitResult>("/api/v1/signing/autofirma/init", {
                method: "POST",
                body: JSON.stringify({
                    signature_format: "PAdES",
                    visible_signature: false,
                    ...req,
                }),
            }),
        /** Estado de la sesión de firma (polling tras lanzar `afirma://`). */
        status: (sessionToken: string) =>
            request<SignedDocumentStatus>(
                `/api/v1/signing/autofirma/status/${sessionToken}`,
            ),
        /**
         * Convierte un File a base64 e inicia la firma. Devuelve la URI
         * `afirma://` lista para asignar a `window.location.href`.
         */
        initFromFile: async (
            file: File,
            opts?: { signature_format?: SignatureFormat; visible_signature?: boolean; document_id?: string },
        ): Promise<AutoFirmaInitResult> => {
            const buf = await file.arrayBuffer();
            const b64 = btoa(String.fromCharCode(...new Uint8Array(buf)));
            return signing.autofirma.init({
                document_b64: b64,
                signature_format: opts?.signature_format,
                visible_signature: opts?.visible_signature,
                document_id: opts?.document_id,
            });
        },
    },
};
