import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type StatusVariant = "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "info";

const STATUS_MAP: Record<string, { label: string; variant: StatusVariant }> = {
    // Invoice statuses
    draft: { label: "Borrador", variant: "secondary" },
    pending: { label: "Pendiente", variant: "warning" },
    sent: { label: "Enviada", variant: "info" },
    paid: { label: "Cobrada", variant: "success" },
    overdue: { label: "Vencida", variant: "destructive" },
    cancelled: { label: "Cancelada", variant: "destructive" },
    partial: { label: "Cobro parcial", variant: "warning" },
    // Employee statuses
    active: { label: "Activo", variant: "success" },
    inactive: { label: "Inactivo", variant: "secondary" },
    leave: { label: "De baja", variant: "warning" },
    terminated: { label: "Cesado", variant: "destructive" },
    // Task statuses
    completed: { label: "Completada", variant: "success" },
    in_progress: { label: "En curso", variant: "info" },
    failed: { label: "Fallida", variant: "destructive" },
    queued: { label: "En cola", variant: "secondary" },
    // Workflow statuses
    running: { label: "Ejecutando", variant: "info" },
    paused: { label: "Pausado", variant: "warning" },
    success: { label: "Éxito", variant: "success" },
    error: { label: "Error", variant: "destructive" },
    // Albaran statuses
    confirmed: { label: "Confirmado", variant: "info" },
    delivered: { label: "Entregado", variant: "success" },
    // Quote statuses
    accepted: { label: "Aceptado", variant: "success" },
    rejected: { label: "Rechazado", variant: "destructive" },
    expired: { label: "Expirado", variant: "secondary" },
    // Banking statuses
    reconciled: { label: "Conciliada", variant: "success" },
    // Generic
    open: { label: "Abierto", variant: "info" },
    closed: { label: "Cerrado", variant: "secondary" },
    approved: { label: "Aprobado", variant: "success" },
};

// Custom variant styles (supplement the default badge variants)
const VARIANT_STYLES: Record<string, string> = {
    success: "bg-success/15 text-success border-success/25 hover:bg-success/20",
    warning: "bg-warning/15 text-warning border-warning/25 hover:bg-warning/20",
    info: "bg-primary/15 text-primary border-primary/25 hover:bg-primary/20",
};

interface StatusBadgeProps {
    status: string;
    label?: string;
    className?: string;
}

export function StatusBadge({ status, label, className }: StatusBadgeProps) {
    const config = STATUS_MAP[status] || { label: status, variant: "secondary" as StatusVariant };
    const displayLabel = label || config.label;
    const variant = config.variant;

    // For custom variants (success, warning, info), apply special styles
    const customStyle = VARIANT_STYLES[variant];

    if (customStyle) {
        return (
            <Badge variant="outline" className={cn("text-[10px] font-semibold uppercase", customStyle, className)}>
                {displayLabel}
            </Badge>
        );
    }

    return (
        <Badge variant={variant as any} className={cn("text-[10px] font-semibold uppercase", className)}>
            {displayLabel}
        </Badge>
    );
}
