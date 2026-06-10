export function fmt(n: number) {
    return n.toLocaleString("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function fmtInt(n: number) {
    return n.toLocaleString("es-ES");
}

export const COLORS_PIE = ["#10b981", "#f59e0b", "#71717a", "#ef4444", "#6366f1", "#06b6d4"];
