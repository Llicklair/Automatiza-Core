/**
 * UI.EMP — componente reutilizable de empty state productivo.
 *
 * Patrón consistente en toda la app:
 *   - Icono Lucide del dominio (decorativo, aria-hidden)
 *   - Título corto y específico (no "No hay datos" genérico)
 *   - Descripción que orienta al usuario sobre qué hacer
 *   - CTA primario (Link interno o callback) — opcional secondaryAction
 *
 * Diseño consensuado en Ronda 25 §50: cada empty state debe responder
 * en menos de 5 segundos a "qué es esto y qué hago ahora".
 */
"use client";

import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { ArrowRight } from "lucide-react";

interface EmptyStateAction {
    label: string;
    href?: string;
    onClick?: () => void;
}

interface EmptyStateProps {
    /** Icono Lucide del dominio. Render decorativo (aria-hidden). */
    icon: LucideIcon;
    /** Frase específica del dominio. Ej.: "Aún no has emitido ninguna factura". */
    title: string;
    /** Texto orientador opcional. Ej.: "Crea tu primera para empezar a cobrar." */
    description?: string;
    /** CTA primario (botón resaltado). */
    action?: EmptyStateAction;
    /** CTA secundario opcional (link sutil, ej.: importar). */
    secondaryAction?: EmptyStateAction;
    /** Tamaño visual; default "md". `sm` para empty states dentro de cards. */
    size?: "sm" | "md";
}

export function EmptyState({
    icon: Icon,
    title,
    description,
    action,
    secondaryAction,
    size = "md",
}: EmptyStateProps) {
    const iconBox =
        size === "sm"
            ? "w-10 h-10 rounded-xl"
            : "w-14 h-14 rounded-2xl";
    const iconSize = size === "sm" ? "w-5 h-5" : "w-7 h-7";
    const padding = size === "sm" ? "py-8 px-4" : "py-16 px-6";

    return (
        <div
            role="status"
            aria-live="polite"
            className={`flex flex-col items-center justify-center text-center ${padding}`}
        >
            <div
                aria-hidden="true"
                className={`${iconBox} bg-primary/10 border border-primary/20 flex items-center justify-center mb-4`}
            >
                <Icon className={`${iconSize} text-primary`} />
            </div>
            <h3
                className={`font-semibold text-foreground ${size === "sm" ? "text-sm" : "text-base"
                    } mb-1.5`}
            >
                {title}
            </h3>
            {description && (
                <p
                    className={`text-muted-foreground max-w-md leading-relaxed ${size === "sm" ? "text-xs" : "text-sm"
                        }`}
                >
                    {description}
                </p>
            )}
            {(action || secondaryAction) && (
                <div className="flex flex-col sm:flex-row items-center gap-2.5 mt-5">
                    {action && <PrimaryButton {...action} />}
                    {secondaryAction && <SecondaryButton {...secondaryAction} />}
                </div>
            )}
        </div>
    );
}

function PrimaryButton({ label, href, onClick }: EmptyStateAction) {
    const cls =
        "inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-primary text-foreground text-sm font-medium hover:bg-primary/90 transition-colors";
    const inner = (
        <>
            <span>{label}</span>
            <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
        </>
    );
    if (href) {
        return (
            <Link href={href} className={cls}>
                {inner}
            </Link>
        );
    }
    return (
        <button type="button" onClick={onClick} className={cls}>
            {inner}
        </button>
    );
}

function SecondaryButton({ label, href, onClick }: EmptyStateAction) {
    const cls =
        "inline-flex items-center gap-1.5 px-3 py-2 rounded-md text-sm text-muted-foreground hover:text-foreground transition-colors";
    if (href) {
        return (
            <Link href={href} className={cls}>
                <span>{label}</span>
            </Link>
        );
    }
    return (
        <button type="button" onClick={onClick} className={cls}>
            <span>{label}</span>
        </button>
    );
}
