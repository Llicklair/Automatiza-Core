export type Tab = "ficha" | "nominas" | "vacaciones" | "gastos";

export const STATUS_BADGE: Record<string, string> = {
    pending:  "bg-amber-500/10 text-amber-400 border-amber-500/20",
    approved: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    rejected: "bg-red-500/10 text-red-400 border-red-500/20",
    draft:    "bg-muted text-muted-foreground border-border",
    paid:     "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
};

export const PAYROLL_LABEL: Record<string, string> = { draft: "Borrador", approved: "Aprobada", paid: "Pagada" };
export const LEAVE_LABEL:   Record<string, string> = { pending: "Pendiente", approved: "Aprobada", rejected: "Rechazada" };
export const LEAVE_TYPES = [
    { value: "vacaciones", label: "Vacaciones" },
    { value: "baja_medica", label: "Baja médica" },
    { value: "excedencia", label: "Excedencia" },
    { value: "otros", label: "Otros" },
];

export const EXPENSE_CATEGORIES = [
    { value: "viaje", label: "Viaje / Transporte" },
    { value: "dieta", label: "Dieta / Manutención" },
    { value: "alojamiento", label: "Alojamiento" },
    { value: "material", label: "Material de oficina" },
    { value: "formacion", label: "Formación" },
    { value: "otro", label: "Otro" },
];

export const EXPENSE_STATUS_LABEL: Record<string, string> = {
    pending: "Pendiente", approved: "Aprobado", rejected: "Rechazado", reimbursed: "Reembolsado",
};
export const EXPENSE_STATUS_STYLE: Record<string, string> = {
    pending:    "bg-amber-500/10 text-amber-400 border-amber-500/20",
    approved:   "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    rejected:   "bg-red-500/10 text-red-400 border-red-500/20",
    reimbursed: "bg-blue-500/10 text-blue-400 border-blue-500/20",
};

export const DAY_LABELS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];

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
