export const RISK_STYLE: Record<string, string> = {
    low: "text-foreground bg-accent border-border",
    medium: "text-amber-300 bg-amber-500/10 border-amber-500/30",
    high: "text-red-300 bg-red-500/10 border-red-500/30",
    critical: "text-red-200 bg-red-700/20 border-red-600/40",
};

export const RISK_LABEL: Record<string, string> = {
    low: "Bajo", medium: "Medio", high: "Alto", critical: "Crítico",
};

export const minutesUntil = (iso: string) => {
    const diff = new Date(iso).getTime() - Date.now();
    return Math.max(0, Math.floor(diff / 60000));
};
