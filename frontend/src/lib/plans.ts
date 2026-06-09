export type PlanTier = "solo" | "pro" | "gestoria" | "dev";

const PLAN_RANK: Record<string, number> = { solo: 1, pro: 2, gestoria: 3, dev: 99 };

export function canAccess(userPlan: string, requiredPlan?: "pro" | "gestoria"): boolean {
    if (!requiredPlan) return true;
    return (PLAN_RANK[userPlan] ?? 0) >= (PLAN_RANK[requiredPlan] ?? 0);
}

export const PLAN_LABELS: Record<string, string> = {
    solo: "Solo",
    pro: "Pro",
    gestoria: "Gestoría",
    dev: "Dev",
};
