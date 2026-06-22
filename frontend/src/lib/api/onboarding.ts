/**
 * UI.ONB + UI.SIM — cliente del wizard onboarding focado + simulación 303.
 */
import { request } from "./client";

export type OnboardingStepKey = "company" | "cert" | "data" | "use_case";

export interface OnboardingState {
    step_company: boolean;
    step_cert: boolean;
    step_data: boolean;
    step_use_case: boolean;
    completed_at: string | null;
    skipped_at: string | null;
    is_dismissed: boolean;
}

export interface Simulate303Row {
    rate: number;
    base: number;
    quota: number;
}

export interface Simulate303Result {
    is_simulation: true;
    year: number;
    quarter: number;
    tenant_name: string;
    tenant_nif: string;
    iva_devengado: Simulate303Row[];
    iva_deducible: Simulate303Row[];
    totals: {
        devengado_base: number;
        devengado_quota: number;
        deducible_base: number;
        deducible_quota: number;
        resultado: number;
    };
    explanation: {
        headline: string;
        bullets: string[];
        footer: string;
    };
}

export interface DemoCounts {
    clients: number;
    products: number;
    invoices: number;
}

export interface DemoSeedResult extends DemoCounts {
    already_seeded: boolean;
}

export interface DemoStatus {
    seeded: boolean;
    counts: DemoCounts;
}

export const onboarding = {
    get: (): Promise<OnboardingState> =>
        request<OnboardingState>("/api/v1/onboarding/wizard"),

    // Datos de ejemplo: siembran/borran una pyme demo (clientes/productos/
    // facturas) para que el producto se vea vivo. No tocan lo fiscal.
    seedDemo: (): Promise<DemoSeedResult> =>
        request<DemoSeedResult>("/api/v1/onboarding/wizard/seed", { method: "POST" }),

    clearDemo: (): Promise<{ deleted: DemoCounts }> =>
        request<{ deleted: DemoCounts }>("/api/v1/onboarding/wizard/seed", {
            method: "DELETE",
        }),

    demoStatus: (): Promise<DemoStatus> =>
        request<DemoStatus>("/api/v1/onboarding/wizard/seed"),

    setStep: (step: OnboardingStepKey, value: boolean): Promise<OnboardingState> =>
        request<OnboardingState>("/api/v1/onboarding/wizard", {
            method: "PATCH",
            body: JSON.stringify({ step, value }),
        }),

    skip: (): Promise<OnboardingState> =>
        request<OnboardingState>("/api/v1/onboarding/wizard/skip", {
            method: "POST",
        }),

    reset: (): Promise<OnboardingState> =>
        request<OnboardingState>("/api/v1/onboarding/wizard/reset", {
            method: "POST",
        }),

    simulate303: (quarter = 1, year = 2026): Promise<Simulate303Result> =>
        request<Simulate303Result>(
            `/api/v1/onboarding/wizard/simulate/303?quarter=${quarter}&year=${year}`,
        ),
};
