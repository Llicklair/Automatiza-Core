"use client";

import { type LucideIcon } from "lucide-react";

export function SectionHeader({ icon: Icon, title, subtitle }: { icon: LucideIcon; title: string; subtitle?: string }) {
    return (
        <div className="flex items-center gap-3 pb-3 border-b border-border">
            <div className="w-9 h-9 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center">
                <Icon className="w-4.5 h-4.5 text-primary" />
            </div>
            <div>
                <h2 className="text-xl font-bold text-foreground tracking-tight">{title}</h2>
                {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
            </div>
        </div>
    );
}
