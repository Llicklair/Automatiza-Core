"use client";

import { useState, useEffect } from "react";
import { AlertTriangle, CalendarClock, MessageSquare, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import { surfaceIfConnectivity } from "@/lib/api/errors";
import { type Vencimiento } from "../_hooks/useCompliance";

function VencimientoCard({ v, urgent }: { v: Vencimiento; urgent?: boolean }) {
    const t = useTranslations("compliance");
    return (
        <div className={`rounded-xl border p-5 ${urgent
            ? "border-amber-500/30 bg-amber-500/5"
            : "border-border bg-card"
            }`}>
            <div className="flex items-start justify-between gap-4">
                <div>
                    <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-bold text-foreground bg-primary/20 text-primary px-2 py-0.5 rounded">
                            {t("calendario.modelo", { modelo: v.modelo })}
                        </span>
                        <span className="font-medium text-foreground text-sm">{v.nombre}</span>
                    </div>
                    <p className="text-xs text-muted-foreground">{v.descripcion}</p>
                </div>
                <div className="text-right flex-shrink-0">
                    <p className="text-sm font-semibold text-foreground">{new Date(v.fecha_limite).toLocaleDateString('es-ES')}</p>
                    <p className={`text-xs ${urgent ? "text-amber-400" : "text-muted-foreground"}`}>
                        {t("calendario.diasRestantes", { count: v.dias_restantes })}
                    </p>
                </div>
            </div>
        </div>
    );
}

export function CalendarioTab() {
    const t = useTranslations("compliance");
    const [vencimientos, setVencimientos] = useState<Vencimiento[]>([]);
    const [alertas, setAlertas] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        api.advisory.calendar(90)
            .then((data) => {
                const list = (data || []) as Vencimiento[];
                setVencimientos(list);
                // Alertas derivadas client-side: lista de modelos que vencen
                // en los próximos `urgente_dias` días.
                const urgentes = list.filter(v => v.dias_restantes <= v.urgente_dias);
                setAlertas(
                    urgentes.map(v =>
                        t("calendario.alerta", {
                            modelo: v.modelo,
                            nombre: v.nombre,
                            count: v.dias_restantes,
                        }),
                    ),
                );
                setLoading(false);
            })
            .catch((err) => {
                setLoading(false);
                if (surfaceIfConnectivity(err)) return;
                setError(err instanceof Error ? err.message : t("calendario.loadError"));
            });
    }, []);

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
                <Loader2 className="w-8 h-8 animate-spin mb-4" />
                <p>{t("calendario.loading")}</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                {t("calendario.loadErrorPrefix", { error })}
            </div>
        );
    }

    const urgentes = vencimientos.filter(v => v.dias_restantes <= v.urgente_dias);
    const proximos = vencimientos.filter(v => v.dias_restantes > v.urgente_dias);

    return (
        <div className="space-y-6">
            {alertas.length > 0 && (
                <div className="rounded-xl border border-primary/20 bg-primary/5 p-5 mb-6">
                    <h2 className="text-sm font-medium text-primary mb-3 flex items-center gap-2">
                        <MessageSquare className="w-4 h-4" />
                        {t("calendario.avisosUrgentes")}
                    </h2>
                    <ul className="space-y-2 text-sm text-foreground list-disc pl-5">
                        {alertas.map((alerta, i) => (
                            <li key={i}>{alerta}</li>
                        ))}
                    </ul>
                </div>
            )}

            {urgentes.length > 0 && (
                <div>
                    <h2 className="text-sm font-medium text-amber-400 mb-3 flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4" />
                        {t("calendario.urgentes")}
                    </h2>
                    <div className="space-y-3">
                        {urgentes.map((v, i) => (
                            <VencimientoCard key={i} v={v} urgent />
                        ))}
                    </div>
                </div>
            )}

            {proximos.length > 0 && (
                <div>
                    <h2 className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
                        <CalendarClock className="w-4 h-4" />
                        {t("calendario.proximos")}
                    </h2>
                    <div className="space-y-3">
                        {proximos.map((v, i) => (
                            <VencimientoCard key={i} v={v} />
                        ))}
                    </div>
                </div>
            )}

            {vencimientos.length === 0 && (
                <div className="text-center py-12 text-muted-foreground text-sm">
                    {t("calendario.empty")}
                </div>
            )}

            <p className="text-xs text-muted-foreground text-center pt-2">
                {t("calendario.disclaimer")}
            </p>
        </div>
    );
}
