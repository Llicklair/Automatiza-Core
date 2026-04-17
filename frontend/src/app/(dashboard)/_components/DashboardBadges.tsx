"use client";

export const STATUS_CONFIG: Record<string, { label: string; color: string; dot: string }> = {
    pending: { label: "Pendiente", color: "text-muted-foreground", dot: "bg-muted-foreground" },
    planning: { label: "Planificando", color: "text-blue-400", dot: "bg-blue-400" },
    executing: { label: "Ejecutando", color: "text-primary", dot: "bg-primary" },
    awaiting_approval: { label: "Aprobación", color: "text-amber-400", dot: "bg-amber-400" },
    done: { label: "Completada", color: "text-emerald-400", dot: "bg-emerald-400" },
    failed: { label: "Fallida", color: "text-red-400", dot: "bg-red-500" },
    cancelled: { label: "Cancelada", color: "text-muted-foreground", dot: "bg-accent" },
};

export function StatusBadge({ status }: { status: string }) {
    const cfg = STATUS_CONFIG[status] ?? { label: status, color: "text-muted-foreground", dot: "bg-muted-foreground" };
    return (
        <span className={`inline-flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1 rounded-full bg-muted border border-border ${cfg.color}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
            {cfg.label}
        </span>
    );
}

export function InvBadge({ status }: { status: string }) {
    switch (status) {
        case 'draft': return <span className="text-[10px] uppercase font-bold text-muted-foreground">Borrador</span>;
        case 'pending': return <span className="text-[10px] uppercase font-bold text-amber-500">Pendiente</span>;
        case 'paid': return <span className="text-[10px] uppercase font-bold text-emerald-500">Cobrada</span>;
        case 'overdue': return <span className="text-[10px] uppercase font-bold text-red-500">Vencida</span>;
        default: return <span className="text-[10px] uppercase font-bold text-muted-foreground">{status}</span>;
    }
}
