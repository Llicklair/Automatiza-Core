import { request } from "./client";

export interface LicenseStatus {
    valid: boolean;
    plan: string;
    key: string | null;
}

export const licenseApi = {
    status: () => request<LicenseStatus>("/api/v1/license/status"),

    activate: (key: string) =>
        request<{ ok: boolean; plan?: string; reason?: string; retriable?: boolean }>("/api/v1/license/activate", {
            method: "POST",
            body: JSON.stringify({ key }),
        }),

    warmup: () =>
        request<{ warming: boolean }>("/api/v1/license/warmup", { method: "POST" }),
};
