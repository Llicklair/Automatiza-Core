/**
 * FAC.MODE — cliente del modo de remisión Verifactu.
 */
import { request } from "./client";

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
};
