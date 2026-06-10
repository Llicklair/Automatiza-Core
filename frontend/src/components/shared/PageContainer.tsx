import { cn } from "@/lib/utils";

/**
 * Wrapper único de página (auditoría UIX #11): padding y max-width
 * consistentes en todas las page.tsx del dashboard.
 *
 * - Padding único `p-6`.
 * - `width` preserva el ancho que cada página ya tenía; "default" es el
 *   ancho del dashboard (1400px). "full" = sin límite (tablas anchas).
 */
const WIDTHS = {
    "3xl": "max-w-3xl",
    "4xl": "max-w-4xl",
    "5xl": "max-w-5xl",
    "6xl": "max-w-6xl",
    "7xl": "max-w-7xl",
    default: "max-w-[1400px]",
    full: "",
} as const;

export type PageWidth = keyof typeof WIDTHS;

interface PageContainerProps {
    width?: PageWidth;
    className?: string;
    children: React.ReactNode;
}

export function PageContainer({
    width = "default",
    className,
    children,
}: PageContainerProps) {
    return (
        <div className={cn("p-6 mx-auto space-y-6", WIDTHS[width], className)}>
            {children}
        </div>
    );
}
