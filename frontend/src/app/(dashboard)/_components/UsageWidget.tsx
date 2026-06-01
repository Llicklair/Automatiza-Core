"use client";

import { useEffect, useState } from "react";
import { Activity, AlertTriangle } from "lucide-react";
import Link from "next/link";
import { llmUsage, type LlmMonthStats } from "@/lib/api/llm_usage";
import { ApiError } from "@/lib/api/errors";

// Soft cap de interacciones del tier Pro (coherente con
// backend/app/services/billing/metering.py · INTERACTION_SOFT_CAP_PRO).
const SOFT_CAP_PRO = 500;
const WARNING_THRESHOLD = 450;

/**
 * Widget de consumo de IA del mes en curso. Da visibilidad del gasto para
 * evitar cargos sorpresa por overage (0,05€/interacción al superar las 500).
 *
 * Fuente: /llm-usage/stats (datos reales de llamadas y coste estimado). El
 * contador de interacciones de facturación (metering.py) aún no está cableado
 * al flujo de request, por eso aquí usamos las llamadas LLM como proxy de
 * "interacciones IA" del mes.
 */
export function UsageWidget() {
    const [month, setMonth] = useState<LlmMonthStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let active = true;
        llmUsage
            .stats(1)
            .then((res) => {
                if (active) setMonth(res.months[0] ?? null);
            })
            .catch((e) => {
                if (active) setError(e instanceof ApiError ? e.detail : "No se pudo cargar el consumo");
            })
            .finally(() => {
                if (active) setLoading(false);
            });
        return () => {
            active = false;
        };
    }, []);

    const calls = month?.total_calls ?? 0;
    const pct = Math.min((calls / SOFT_CAP_PRO) * 100, 100);
    const overage = calls > SOFT_CAP_PRO;
    const warning = calls >= WARNING_THRESHOLD && calls <= SOFT_CAP_PRO;
    const barColor = overage ? "bg-red-500" : warning ? "bg-yellow-400" : "bg-primary";
    const cost = month?.estimated_cost_usd ?? 0;

    return (
        <div className="bg-card border border-border rounded-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-border bg-card flex items-center justify-between">
                <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                    <Activity className="w-4 h-4 text-primary" /> Consumo de IA
                </h2>
                <span className="text-[10px] text-muted-foreground uppercase tracking-wide">Este mes</span>
            </div>

            <div className="p-5">
                {loading ? (
                    <div className="h-16 animate-pulse rounded-lg bg-muted/50" />
                ) : error ? (
                    <p className="text-xs text-muted-foreground">{error}</p>
                ) : (
                    <>
                        <div className="flex items-end justify-between">
                            <div>
                                <p className="text-2xl font-bold text-foreground tabular-nums">
                                    {calls.toLocaleString("es-ES")}
                                    <span className="text-sm font-normal text-muted-foreground"> / {SOFT_CAP_PRO}</span>
                                </p>
                                <p className="text-[11px] text-muted-foreground mt-0.5">interacciones IA</p>
                            </div>
                            <p className="text-xs text-muted-foreground">
                                ≈ ${cost.toFixed(2)}
                            </p>
                        </div>

                        <div className="mt-3 h-2 w-full rounded-full bg-muted overflow-hidden">
                            <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: `${pct}%` }} />
                        </div>

                        {(warning || overage) && (
                            <p className={`mt-2 text-[11px] flex items-center gap-1 ${overage ? "text-red-400" : "text-yellow-400"}`}>
                                <AlertTriangle className="w-3 h-3" />
                                {overage
                                    ? "Has superado las 500 interacciones: 0,05€ + IVA por extra."
                                    : `Has usado ${calls} de ${SOFT_CAP_PRO} interacciones este mes.`}
                            </p>
                        )}
                    </>
                )}
            </div>

            <div className="p-3 border-t border-border bg-muted/50 text-center">
                <Link
                    href="/configuracion/api-keys"
                    className="text-[11px] font-medium text-muted-foreground hover:text-foreground transition-colors"
                >
                    Ver detalle de consumo
                </Link>
            </div>
        </div>
    );
}
