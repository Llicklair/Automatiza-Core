"use client";

import { ArrowUp, ArrowDown, type LucideIcon } from "lucide-react";

export function KpiCard({
    label, value, sub, icon: Icon, trend, color = "indigo"
}: {
    label: string; value: string; sub?: string; icon: LucideIcon;
    trend?: { dir: "up" | "down"; pct: number }; color?: "indigo" | "emerald" | "red" | "amber";
}) {
    const colors = {
        indigo: "border-primary/20 from-indigo-900/20 text-primary bg-primary/10",
        emerald: "border-emerald-500/20 from-emerald-900/20 text-emerald-400 bg-emerald-500/10",
        red: "border-red-500/20 from-red-900/20 text-red-400 bg-red-500/10",
        amber: "border-amber-500/20 from-amber-900/20 text-amber-400 bg-amber-500/10",
    };
    const c = colors[color];
    return (
        <div className={`rounded-2xl border ${c.split(" ")[0]} bg-gradient-to-br from-card ${c.split(" ")[1]} p-6 relative overflow-hidden group`}>
            <div className={`absolute -right-4 -top-4 w-24 h-24 ${c.split(" ")[3]}/30 rounded-full blur-2xl group-hover:scale-110 transition-transform duration-700`} />
            <div className="flex items-start justify-between mb-4 relative">
                <div className={`w-10 h-10 rounded-xl ${c.split(" ")[3]} border ${c.split(" ")[0]} flex items-center justify-center`}>
                    <Icon className={`w-5 h-5 ${c.split(" ")[2]}`} />
                </div>
                {trend && (
                    <span className={`flex items-center gap-1 text-xs font-bold px-2 py-1 rounded-full ${trend.dir === "up"
                        ? "bg-emerald-500/10 text-emerald-400"
                        : "bg-red-500/10 text-red-400"
                        }`}>
                        {trend.dir === "up" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />}
                        {trend.pct}%
                    </span>
                )}
            </div>
            <p className="text-xs text-muted-foreground mb-1 font-medium uppercase tracking-wide">{label}</p>
            <p className="text-3xl font-bold text-foreground tracking-tight">{value}</p>
            {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
        </div>
    );
}
