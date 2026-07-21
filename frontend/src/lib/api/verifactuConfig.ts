/**
 * FAC.MODE — cliente del modo de remisión Verifactu.
 */
import { request, fetchBlob, downloadBlob } from "./client";

export type VerifactuMode = "voluntary" | "no_remission";

export interface VerifactuConfig {
    mode: VerifactuMode;
    updated_at: string;
    is_default: boolean;
}

export const verifactuConfig = {
    get: (): Promise<VerifactuConfig> =>
        request<VerifactuConfig>("/api/v1/verifactu/config"),

    set: (mode: VerifactuMode): Promise<VerifactuConfig> =>
        request<VerifactuConfig>("/api/v1/verifactu/config", {
            method: "PUT",
            body: JSON.stringify({ mode }),
        }),

    // Documento de la declaración responsable del productor (art. 15).
    declaracionResponsable: (): Promise<Blob> =>
        fetchBlob("/api/v1/verifactu/config/declaracion-responsable"),

    descargarDeclaracionResponsable: (): Promise<void> =>
        downloadBlob("/api/v1/verifactu/config/declaracion-responsable", "declaracion-responsable.txt"),
};
