"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { Lock, ArrowRight } from "lucide-react";
import { useLicenseStore } from "@/stores/license";
import { canAccess } from "@/lib/plans";
import { requiredPlanForPath } from "@/components/layout/nav-config";

/**
 * Guard de página: si la ruta actual exige un plan superior al del usuario,
 * bloquea el render con una pantalla de mejora en vez de dejar cargar la página.
 * Es la capa de UX; el candado autoritativo está en el backend (require_plan).
 *
 * Solo bloquea cuando el plan es CONOCIDO (no "" inicial) para no parpadear un
 * bloqueo falso mientras el plan aún se carga.
 */
export function PlanGuard({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const plan = useLicenseStore((s) => s.plan);
    const required = requiredPlanForPath(pathname);

    if (required && plan && !canAccess(plan, required)) {
        return <PlanLocked required={required} />;
    }
    return <>{children}</>;
}

function PlanLocked({ required }: { required: "pro" | "gestoria" }) {
    const t = useTranslations("planGuard");
    const planName = required === "gestoria" ? "Gestoría" : "Pro";
    return (
        <div className="flex flex-col items-center justify-center min-h-[70vh] px-6 text-center">
            <div className="w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mb-5">
                <Lock className="w-6 h-6 text-primary" />
            </div>
            <h1 className="text-2xl font-bold text-foreground mb-2">{t("title", { plan: planName })}</h1>
            <p className="text-muted-foreground max-w-md mb-6">{t("body", { plan: planName })}</p>
            <Link
                href="/configuracion"
                className="inline-flex items-center gap-2 bg-primary hover:bg-primary/90 text-foreground px-5 py-2.5 rounded-xl font-medium transition-colors"
            >
                {t("cta")} <ArrowRight className="w-4 h-4" />
            </Link>
        </div>
    );
}
