/**
 * @deprecated Usa `@/components/ui/EmptyState` (tipado, ARIA, sizes).
 *
 * Mantenemos este wrapper de compatibilidad mientras se migran los ~10
 * callsites existentes. La API legacy acepta `action` como JSX libre;
 * la nueva acepta `action: { label, href, onClick }`.
 *
 * Diferencia visual: el legacy usaba `bg-muted` (gris sutil). El nuevo
 * usa `bg-primary/10` (acento). Para preservar visualmente las páginas
 * legacy hasta migrarlas, este wrapper conserva el estilo gris.
 */
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
    icon?: LucideIcon;
    title: string;
    description?: string;
    action?: React.ReactNode;
    className?: string;
}

export function EmptyState({
    icon: Icon,
    title,
    description,
    action,
    className,
}: EmptyStateProps) {
    return (
        <div
            role="status"
            aria-live="polite"
            className={cn(
                "flex flex-col items-center justify-center py-12 text-center",
                className,
            )}
        >
            {Icon && (
                <div
                    aria-hidden="true"
                    className="flex h-14 w-14 items-center justify-center rounded-full bg-muted mb-4"
                >
                    <Icon className="h-6 w-6 text-muted-foreground" />
                </div>
            )}
            <h3 className="text-sm font-semibold text-foreground">{title}</h3>
            {description && (
                <p className="mt-1 text-sm text-muted-foreground max-w-sm">
                    {description}
                </p>
            )}
            {action && <div className="mt-4">{action}</div>}
        </div>
    );
}
