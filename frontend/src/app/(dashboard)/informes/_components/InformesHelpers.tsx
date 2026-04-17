"use client";

import React from "react";

// ─── KPI Card ─────────────────────────────────────────────────────────────────

export function KpiCard({ label, value, sub, icon: Icon, color = "indigo" }: {
    label: string; value: string; sub?: string; icon: any;
    color?: "indigo" | "emerald" | "red" | "amber" | "blue" | "purple";
}) {
    const cls: Record<string, string> = {
        indigo: "border-primary/20 bg-primary/10 text-primary",
        emerald: "border-emerald-500/20 bg-emerald-500/10 text-emerald-400",
        red: "border-red-500/20 bg-red-500/10 text-red-400",
        amber: "border-amber-500/20 bg-amber-500/10 text-amber-400",
        blue: "border-blue-500/20 bg-blue-500/10 text-blue-400",
        purple: "border-purple-500/20 bg-purple-500/10 text-purple-400",
    };
    const c = cls[color];
    return (
        <div className="rounded-2xl border border-border bg-card p-5 flex flex-col gap-3">
            <div className="flex items-center gap-3">
                <div className={`w-9 h-9 rounded-xl border ${c} flex items-center justify-center shrink-0`}>
                    <Icon className={`w-4 h-4 ${c.split(" ")[2]}`} />
                </div>
                <span className="text-xs text-muted-foreground font-medium">{label}</span>
            </div>
            <div>
                <p className="text-xl font-bold text-foreground">{value}</p>
                {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
            </div>
        </div>
    );
}

// ─── Section ──────────────────────────────────────────────────────────────────

export function Section({ title, icon: Icon, children }: { title: string; icon: any; children: React.ReactNode }) {
    return (
        <div className="rounded-2xl border border-border bg-card overflow-hidden">
            <div className="flex items-center gap-2 px-5 py-3 border-b border-border">
                <Icon className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm font-semibold text-foreground">{title}</span>
            </div>
            <div className="p-5">{children}</div>
        </div>
    );
}

// ─── Row ──────────────────────────────────────────────────────────────────────

export function Row({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
    return (
        <div className={`flex justify-between py-2 border-b border-border last:border-0 ${highlight ? "text-foreground" : "text-muted-foreground"}`}>
            <span className="text-sm">{label}</span>
            <span className={`text-sm font-semibold ${highlight ? "text-foreground" : "text-foreground"}`}>{value}</span>
        </div>
    );
}

// ─── Tab Button ───────────────────────────────────────────────────────────────

export function TabBtn({ active, label, icon: Icon, onClick }: {
    active: boolean; label: string; icon: any; onClick: () => void;
}) {
    return (
        <button
            onClick={onClick}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-colors ${
                active
                    ? "bg-accent text-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
            }`}
        >
            <Icon className="w-4 h-4" />
            {label}
        </button>
    );
}
