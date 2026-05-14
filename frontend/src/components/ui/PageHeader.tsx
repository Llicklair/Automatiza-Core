/**
 * UI.POL — encabezado de página canónico.
 *
 * Patrón consistente para todas las páginas del dashboard:
 *   - h1 con tipografía estándar (text-2xl font-semibold tracking-tight)
 *   - Descripción opcional con text-sm muted-foreground
 *   - Acciones a la derecha (botones primario + secundario)
 *   - Separación inferior estándar mb-6
 *
 * Usar este componente en lugar de copiar el patrón en cada page.tsx
 * garantiza consistencia visual y semántica accesible (siempre h1 una
 * vez por página, con landmark de heading detectable por SR).
 */
"use client";

import type { ReactNode } from "react";

interface PageHeaderProps {
    title: string;
    description?: string;
    /** Acciones a la derecha (botones, dropdowns). */
    actions?: ReactNode;
    /** Breadcrumb opcional renderizado encima del título. */
    breadcrumb?: ReactNode;
}

export function PageHeader({ title, description, actions, breadcrumb }: PageHeaderProps) {
    return (
        <header className="mb-6">
            {breadcrumb && <div className="mb-2">{breadcrumb}</div>}
            <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                    <h1 className="text-2xl font-semibold text-foreground tracking-tight truncate">
                        {title}
                    </h1>
                    {description && (
                        <p className="mt-1 text-sm text-muted-foreground">
                            {description}
                        </p>
                    )}
                </div>
                {actions && (
                    <div className="flex items-center gap-2 flex-shrink-0">
                        {actions}
                    </div>
                )}
            </div>
        </header>
    );
}
