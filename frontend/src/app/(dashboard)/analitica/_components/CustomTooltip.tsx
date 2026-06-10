"use client";

import { fmt } from "./utils";

interface TooltipPayloadEntry {
    value: number;
    name: string;
    color: string;
}

export const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: TooltipPayloadEntry[]; label?: string }) => {
    if (active && payload?.length) {
        return (
            <div className="bg-card border border-border rounded-xl p-3 text-xs shadow-xl">
                <p className="text-muted-foreground mb-2 font-medium">{label}</p>
                {payload.map((p) => (
                    <p key={p.name} style={{ color: p.color }} className="font-semibold">
                        {p.name}: {fmt(p.value)}€
                    </p>
                ))}
            </div>
        );
    }
    return null;
};
