export type Tab = "ficha" | "nominas" | "vacaciones" | "gastos";

export const STATUS_BADGE: Record<string, string> = {
    pending:  "bg-amber-500/10 text-amber-400 border-amber-500/20",
    approved: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    rejected: "bg-red-500/10 text-red-400 border-red-500/20",
    draft:    "bg-muted text-muted-foreground border-border",
    paid:     "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
};

export const LEAVE_TYPE_VALUES = ["vacaciones", "baja_medica", "excedencia", "otros"] as const;
export const EXPENSE_CATEGORY_VALUES = ["viaje", "dieta", "alojamiento", "material", "formacion", "otro"] as const;

export const EXPENSE_STATUS_STYLE: Record<string, string> = {
    pending:    "bg-amber-500/10 text-amber-400 border-amber-500/20",
    approved:   "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    rejected:   "bg-red-500/10 text-red-400 border-red-500/20",
    reimbursed: "bg-blue-500/10 text-blue-400 border-blue-500/20",
};

export const DAY_KEYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"] as const;

export function fmt(d: string) {
    return new Date(d).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" });
}
export function currency(n: number) {
    return new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(n);
}
export function formatClockTime(iso: string | null | undefined) {
    if (!iso) return "—";
    return new Date(iso).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
}
