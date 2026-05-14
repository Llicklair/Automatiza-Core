/**
 * SEC.AUT — cliente de política de autonomía por dominio.
 */
import { request } from "./client";

export type AutonomyMode = "AUTO" | "CONFIRM" | "MANUAL";

export interface PolicyEntry {
    mode: AutonomyMode;
    is_default: boolean;
}

export interface PolicyList {
    policies: Record<string, PolicyEntry>;
    known_domains: string[];
}

export const autonomy = {
    list: (): Promise<PolicyList> => request<PolicyList>("/api/v1/autonomy"),

    set: (domain: string, mode: AutonomyMode): Promise<PolicyEntry> =>
        request<PolicyEntry>(`/api/v1/autonomy/${encodeURIComponent(domain)}`, {
            method: "PUT",
            body: JSON.stringify({ mode }),
        }),

    reset: (domain: string): Promise<void> =>
        request<void>(`/api/v1/autonomy/${encodeURIComponent(domain)}`, {
            method: "DELETE",
        }),
};
