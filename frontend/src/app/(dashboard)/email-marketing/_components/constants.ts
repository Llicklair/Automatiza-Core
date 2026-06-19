export const errMsg = (err: unknown, fallback: string) =>
    err instanceof Error ? err.message : fallback;

export const fmt = (iso: string | null) =>
    iso ? new Date(iso).toLocaleString("es-ES", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "—";
