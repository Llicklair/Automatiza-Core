"use client";

import { CheckCircle2, Loader2, XCircle, Clock, Pause, MinusCircle } from "lucide-react";

interface NodeStatusBadgeProps {
    status: string | undefined;
    size?: "sm" | "md";
}

const STATUS_CONFIG: Record<string, { icon: React.ElementType; cls: string; label: string }> = {
    completed: { icon: CheckCircle2, cls: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20", label: "Completado" },
    running: { icon: Loader2, cls: "text-blue-400 bg-blue-500/10 border-blue-500/20", label: "Ejecutando" },
    failed: { icon: XCircle, cls: "text-red-400 bg-red-500/10 border-red-500/20", label: "Error" },
    waiting: { icon: Clock, cls: "text-blue-400 bg-blue-500/10 border-blue-500/20", label: "Esperando" },
    paused: { icon: Pause, cls: "text-orange-400 bg-orange-500/10 border-orange-500/20", label: "Pausado" },
    skipped: { icon: MinusCircle, cls: "text-muted-foreground bg-muted border-border line-through", label: "Omitido" },
    pending: { icon: Clock, cls: "text-muted-foreground bg-muted border-border", label: "Pendiente" },
};

export default function NodeStatusBadge({ status, size = "sm" }: NodeStatusBadgeProps) {
    if (!status) return null;
    const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
    const Icon = config.icon;
    const iconSize = size === "sm" ? "w-3 h-3" : "w-4 h-4";
    const textSize = size === "sm" ? "text-[10px]" : "text-xs";

    return (
        <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded border font-semibold ${textSize} ${config.cls}`}>
            <Icon className={`${iconSize} ${status === "running" ? "animate-spin" : ""}`} />
            {config.label}
        </span>
    );
}
