/**
 * UI.DEN — Settings de preferencias de UI (densidad).
 */
"use client";

import { CheckCircle2, Layout, LayoutList } from "lucide-react";
import { useDensity, type Density } from "@/hooks/useDensity";

const OPTIONS: { value: Density; label: string; description: string; icon: typeof Layout }[] = [
    {
        value: "comfortable",
        label: "Cómodo",
        description:
            "Mayor espaciado y tipografías más amplias. Apto para PYMEs con uso ocasional.",
        icon: Layout,
    },
    {
        value: "compact",
        label: "Compacto",
        description:
            "Más filas en pantalla, padding reducido. Pensado para gestorías que consultan muchos registros.",
        icon: LayoutList,
    },
];

export default function PreferenciasPage() {
    const { density, setDensity } = useDensity();

    return (
        <div className="p-6 max-w-3xl space-y-6">
            <header>
                <h1 className="text-2xl font-semibold text-foreground tracking-tight">
                    Preferencias de visualización
                </h1>
                <p className="mt-1 text-sm text-muted-foreground">
                    Ajusta la densidad de la interfaz a tu flujo de trabajo. El cambio se
                    aplica al instante y se guarda en este equipo.
                </p>
            </header>

            <section aria-labelledby="density-heading">
                <h2
                    id="density-heading"
                    className="text-sm font-medium text-foreground mb-3"
                >
                    Densidad de la interfaz
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
                                            aria-label="Activo"
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
                La preferencia se guarda solo en este navegador. Si entras desde otro
                equipo, deberás volver a elegirla.
            </aside>
        </div>
    );
}
