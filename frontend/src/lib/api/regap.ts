/**
 * PRES.REG — cliente del wizard REGAP (apoderamiento AEAT).
 */
import { request } from "./client";

export type RegapStatusValue =
    | "not_started"
    | "identifying"
    | "cert_pending"
    | "power_granted"
    | "verified"
    | "rejected";

export type RegapAuthMethod = "clave_pin" | "clave_permanente" | "cert_fnmt";

export interface RegapStatus {
    status: RegapStatusValue;
    auth_method: RegapAuthMethod | null;
    apoderado_nif: string | null;
    apoderado_nombre: string | null;
    verified_at: string | null;
    rejected_reason: string | null;
}

export const regap = {
    get: (): Promise<RegapStatus> =>
        request<RegapStatus>("/api/v1/onboarding/regap"),

    start: (authMethod: RegapAuthMethod): Promise<RegapStatus> =>
        request<RegapStatus>("/api/v1/onboarding/regap/start", {
            method: "POST",
            body: JSON.stringify({ auth_method: authMethod }),
        }),

    grant: (): Promise<RegapStatus> =>
        request<RegapStatus>("/api/v1/onboarding/regap/grant", {
            method: "POST",
        }),

    verify: (nifCliente: string): Promise<RegapStatus> =>
        request<RegapStatus>("/api/v1/onboarding/regap/verify", {
            method: "POST",
            body: JSON.stringify({ nif_cliente: nifCliente }),
        }),

    reset: (): Promise<RegapStatus> =>
        request<RegapStatus>("/api/v1/onboarding/regap/reset", {
            method: "POST",
        }),
};
