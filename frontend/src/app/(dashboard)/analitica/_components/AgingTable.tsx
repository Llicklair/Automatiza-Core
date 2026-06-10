"use client";

import { TrendingUp, TrendingDown } from "lucide-react";
import { fmt } from "./utils";

const AGING_LABELS: { key: keyof import("@/lib/api").AnalyticsAgingBuckets; label: string; bad?: boolean }[] = [
    { key: "vencido_90", label: "Vencido > 90 d", bad: true },
    { key: "vencido_60_90", label: "Vencido 60-90 d", bad: true },
    { key: "vencido_30_60", label: "Vencido 30-60 d", bad: true },
    { key: "vencido_0_30", label: "Vencido 0-30 d", bad: true },
    { key: "vence_0_30", label: "Vence en 0-30 d" },
    { key: "vence_30plus", label: "Vence en > 30 d" },
];

export function AgingTable({
    title, subtitle, buckets, color,
}: {
    title: string; subtitle: string;
    buckets: import("@/lib/api").AnalyticsAgingBuckets;
    color: "emerald" | "red";
}) {
    const total = AGING_LABELS.reduce((s, b) => s + buckets[b.key].importe, 0);
    const empty = total === 0;
    const Icon = color === "emerald" ? TrendingUp : TrendingDown;
    return (
        <div className="bg-card border border-border rounded-2xl p-6">
            <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                <Icon className={`w-4 h-4 ${color === "emerald" ? "text-emerald-400" : "text-red-400"}`} /> {title}
            </h2>
            <p className="text-xs text-muted-foreground mb-5">{subtitle}</p>
            {empty ? (
                <div className="h-[180px] flex items-center justify-center text-sm text-muted-foreground">
                    Sin importes pendientes
                </div>
            ) : (
                <div className="space-y-3">
                    {AGING_LABELS.map(b => {
                        const v = buckets[b.key];
                        const pct = total > 0 ? (v.importe / total) * 100 : 0;
                        return (
                            <div key={String(b.key)}>
                                <div className="flex items-center justify-between text-xs mb-1">
                                    <span className={b.bad ? "text-red-400 font-medium" : "text-muted-foreground"}>{b.label}</span>
                                    <span className="text-foreground font-semibold">{v.n} · {fmt(v.importe)}€</span>
                                </div>
                                <div className="w-full h-1.5 bg-border rounded-full overflow-hidden">
                                    <div
                                        className={`h-full rounded-full transition-all duration-700 ${b.bad ? "bg-red-500/70" : "bg-emerald-500/70"}`}
                                        style={{ width: `${pct}%` }}
                                    />
                                </div>
                            </div>
                        );
                    })}
                    <div className="pt-3 mt-3 border-t border-border flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">Total pendiente</span>
                        <span className="text-foreground font-bold">{fmt(total)}€</span>
                    </div>
                </div>
            )}
        </div>
    );
}
