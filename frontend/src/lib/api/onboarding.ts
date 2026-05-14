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

export const onboarding = {
    get: (): Promise<OnboardingState> =>
        request<OnboardingState>("/api/v1/onboarding/wizard"),

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
