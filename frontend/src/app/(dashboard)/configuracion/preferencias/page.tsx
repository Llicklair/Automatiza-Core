/**
 * UI.DEN — Settings de preferencias de UI (densidad).
 */
"use client";

import { CheckCircle2, Layout, LayoutList } from "lucide-react";
import { useTranslations } from "next-intl";
import { useDensity, type Density } from "@/hooks/useDensity";
import { PageContainer } from "@/components/shared/PageContainer";

type DensityOption = { value: Density; label: string; description: string; icon: typeof Layout };

const buildOptions = (t: (k: string) => string): DensityOption[] => [
    {
        value: "comfortable",
        label: t("preferencias.comfortable.label"),
        description: t("preferencias.comfortable.description"),
        icon: Layout,
    },
    {
        value: "compact",
        label: t("preferencias.compact.label"),
        description: t("preferencias.compact.description"),
        icon: LayoutList,
    },
];

export default function PreferenciasPage() {
    const t = useTranslations("configuracion");
    const { density, setDensity } = useDensity();
    const OPTIONS = buildOptions(t);

    return (
        <PageContainer width="3xl">
            <header>
                <h1 className="text-2xl font-semibold text-foreground tracking-tight">
                    {t("preferencias.title")}
                </h1>
                <p className="mt-1 text-sm text-muted-foreground">
                    {t("preferencias.subtitle")}
                </p>
            </header>

            <section aria-labelledby="density-heading">
                <h2
                    id="density-heading"
                    className="text-sm font-medium text-foreground mb-3"
                >
                    {t("preferencias.densityHeading")}
                </h2>
                <div
                    role="radiogroup"
                    aria-labelledby="density-heading"
                    className="grid grid-cols-1 md:grid-cols-2 gap-3"
                >
                    {OPTIONS.map((opt) => {
                        const Icon = opt.icon;
                        const active = density === opt.value;
                        return (
                            <button
                                key={opt.value}
                                type="button"
                                role="radio"
                                aria-checked={active}
                                onClick={() => setDensity(opt.value)}
                                className={`text-left rounded-lg border p-4 transition-colors ${active
                                    ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                                    : "border-border bg-card hover:border-primary/50"
                                    }`}
                            >
                                <div className="flex items-center justify-between mb-1.5">
                                    <div className="flex items-center gap-2">
                                        <Icon className="w-4 h-4 text-primary" aria-hidden="true" />
                                        <span className="text-sm font-semibold text-foreground">
                                            {opt.label}
                                        </span>
                                    </div>
                                    {active && (
                                        <CheckCircle2
                                            className="w-4 h-4 text-primary"
                                            aria-label={t("preferencias.active")}
                                        />
                                    )}
                                </div>
                                <p className="text-xs text-muted-foreground leading-relaxed">
                                    {opt.description}
                                </p>
                            </button>
                        );
                    })}
                </div>
            </section>

            <aside className="text-xs text-muted-foreground">
                {t("preferencias.footnote")}
            </aside>
        </PageContainer>
    );
}
