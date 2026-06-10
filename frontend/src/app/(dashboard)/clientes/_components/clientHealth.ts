import { Client } from "@/lib/api";

// ── Helpers ───────────────────────────────────────────────────────────────────

export function getInitials(name: string) {
    return name.split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
}

export type HealthLevel = "complete" | "partial" | "incomplete";

export function clientHealth(c: Client): HealthLevel {
    const hasContact = !!(c.email || c.phone);
    const hasNif = !!c.nif;
    if (hasContact && hasNif) return "complete";
    if (hasContact || hasNif) return "partial";
    return "incomplete";
}

export const HEALTH_CONFIG: Record<HealthLevel, { dot: string; ring: string; label: string }> = {
    complete:   { dot: "bg-emerald-400", ring: "ring-emerald-400/30", label: "Datos completos" },
    partial:    { dot: "bg-amber-400",   ring: "ring-amber-400/30",   label: "Datos parciales" },
    incomplete: { dot: "bg-red-400",     ring: "ring-red-400/30",     label: "Sin contacto" },
};

// ── Shared types ──────────────────────────────────────────────────────────────

export type ClientTypeMap = Record<string, { label: string; variant: "info" | "warning" | "default" | "success" }>;

export type ClientTypeOption = { label: string; value: string };
