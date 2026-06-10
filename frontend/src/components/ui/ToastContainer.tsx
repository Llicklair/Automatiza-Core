"use client";

/**
 * Renderer global del toast store (stores/toast.ts).
 *
 * Hasta la auditoría UIX #12 el store no tenía UI: los toast.error/success
 * de toda la app no se mostraban (solo sonner, usado en una página, pintaba
 * algo). Este contenedor es el único sistema de toasts; sonner se retiró.
 */

import { AlertCircle, AlertTriangle, CheckCircle2, Info, X } from "lucide-react";
import { useToastStore, type ToastType } from "@/stores/toast";

const STYLES: Record<ToastType, { box: string; icon: typeof Info }> = {
    success: { box: "border-emerald-500/30 text-emerald-500", icon: CheckCircle2 },
    error: { box: "border-red-500/30 text-red-400", icon: AlertCircle },
    warning: { box: "border-amber-500/30 text-amber-500", icon: AlertTriangle },
    info: { box: "border-border text-muted-foreground", icon: Info },
};

export function ToastContainer() {
    const toasts = useToastStore((s) => s.toasts);
    const dismiss = useToastStore((s) => s.dismiss);

    if (toasts.length === 0) return null;

    return (
        <div
            aria-live="polite"
            className="fixed bottom-4 right-4 z-[100] flex w-80 flex-col gap-2"
        >
            {toasts.map((t) => {
                const { box, icon: Icon } = STYLES[t.type];
                return (
                    <div
                        key={t.id}
                        role="status"
                        className={`flex items-start gap-2 rounded-lg border bg-card p-3 shadow-lg ${box}`}
                    >
                        <Icon className="mt-0.5 h-4 w-4 flex-shrink-0" aria-hidden="true" />
                        <p className="flex-1 text-sm text-foreground leading-snug break-words">
                            {t.message}
                        </p>
                        <button
                            type="button"
                            onClick={() => dismiss(t.id)}
                            aria-label="Cerrar notificación"
                            className="text-muted-foreground hover:text-foreground"
                        >
                            <X className="h-4 w-4" />
                        </button>
                    </div>
                );
            })}
        </div>
    );
}
