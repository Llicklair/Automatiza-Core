"use client";

import {
    Zap, BrainCircuit, Clock, CheckCircle2, XCircle,
    Coins, Timer, Cpu, AlertCircle,
} from "lucide-react";
import type { AnalyticsDashboard } from "@/lib/api";
import { KpiCard } from "./KpiCard";
import { SectionHeader } from "./SectionHeader";
import { fmt, fmtInt } from "./utils";

interface IaSectionProps {
    periodLabel: string;
    ia: AnalyticsDashboard["ia"];
    iaDetalle: AnalyticsDashboard["ia_detalle"];
    tasksDone: number;
    tasksFailed: number;
    tasksSuccessRate: number;
    tasksPending: number;
}

export function IaSection({
    periodLabel, ia, iaDetalle,
    tasksDone, tasksFailed, tasksSuccessRate, tasksPending,
}: IaSectionProps) {
    return (
        <section className="space-y-6">
            <SectionHeader icon={BrainCircuit} title="IA / Agentes" subtitle="Ejecuciones, tokens, coste y errores" />
            {/* KPIs IA — fila 1: tasks */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                <KpiCard
                    label="Tasa de éxito"
                    value={`${tasksSuccessRate}%`}
                    sub="Fiabilidad global"
                    icon={Zap}
                    color="indigo"
                />
                <KpiCard
                    label="Completadas"
                    value={`${tasksDone}`}
                    icon={CheckCircle2}
                    color="emerald"
                />
                <KpiCard
                    label="En curso"
                    value={`${tasksPending}`}
                    icon={Clock}
                    color="amber"
                />
                <KpiCard
                    label="Fallidas"
                    value={`${tasksFailed}`}
                    icon={XCircle}
                    color="red"
                />
            </div>

            {/* KPIs IA — fila 2: cost & latency */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                <KpiCard
                    label="Tokens consumidos"
                    value={fmtInt(ia.tokens_total_periodo)}
                    sub={`Periodo: ${periodLabel}`}
                    icon={Cpu}
                    color="indigo"
                />
                <KpiCard
                    label="Coste IA"
                    value={`${fmt(ia.coste_total_periodo_eur)}€`}
                    sub="Suma de llamadas LLM"
                    icon={Coins}
                    color="amber"
                />
                <KpiCard
                    label="Latencia media"
                    value={`${ia.tiempo_medio_ms} ms`}
                    sub="Por ejecución de agente"
                    icon={Timer}
                    color="emerald"
                />
            </div>

            {/* Desglose por agente */}
            <div className="bg-card border border-border rounded-2xl p-6">
                <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                    <BrainCircuit className="w-4 h-4 text-primary" /> Rendimiento por agente
                </h2>
                <p className="text-xs text-muted-foreground mb-5">Top 10 agentes más usados en {periodLabel}</p>
                {iaDetalle.por_agente.length === 0 ? (
                    <div className="h-[140px] flex items-center justify-center text-sm text-muted-foreground">
                        Sin ejecuciones de agentes en este periodo
                    </div>
                ) : (
                    <div className="overflow-x-auto rounded-xl border border-border">
                        <table className="w-full text-xs">
                            <thead className="bg-muted">
                                <tr>
                                    <th className="text-left py-2 px-3 text-muted-foreground font-medium">Agente</th>
                                    <th className="text-right py-2 px-3 text-muted-foreground font-medium">Ejec.</th>
                                    <th className="text-right py-2 px-3 text-muted-foreground font-medium">Éxito</th>
                                    <th className="text-right py-2 px-3 text-muted-foreground font-medium">Tokens (in/out)</th>
                                    <th className="text-right py-2 px-3 text-muted-foreground font-medium">Coste</th>
                                    <th className="text-right py-2 px-3 text-muted-foreground font-medium">Latencia</th>
                                </tr>
                            </thead>
                            <tbody>
                                {iaDetalle.por_agente.map(a => (
                                    <tr key={a.agent} className="border-t border-border">
                                        <td className="py-2 px-3 text-foreground font-medium">{a.agent}</td>
                                        <td className="py-2 px-3 text-right text-foreground">{a.ejecuciones}</td>
                                        <td className={`py-2 px-3 text-right font-semibold ${a.exito_pct >= 90 ? "text-emerald-400" : a.exito_pct >= 70 ? "text-amber-400" : "text-red-400"}`}>
                                            {a.exito_pct}%
                                        </td>
                                        <td className="py-2 px-3 text-right text-foreground">
                                            {fmtInt(a.tokens_in)} / {fmtInt(a.tokens_out)}
                                        </td>
                                        <td className="py-2 px-3 text-right text-foreground">{fmt(a.coste_eur)}€</td>
                                        <td className="py-2 px-3 text-right text-foreground">{a.duracion_media_ms} ms</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Top errores */}
            <div className="bg-card border border-border rounded-2xl p-6">
                <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-red-400" /> Errores más frecuentes
                </h2>
                <p className="text-xs text-muted-foreground mb-5">Tipos de error en ejecuciones fallidas</p>
                {iaDetalle.top_errores.length === 0 ? (
                    <div className="h-[100px] flex items-center justify-center text-sm text-muted-foreground">
                        Sin errores registrados
                    </div>
                ) : (
                    <div className="space-y-3">
                        {iaDetalle.top_errores.map((e, i) => {
                            const max = iaDetalle.top_errores[0].count || 1;
                            const pct = Math.round((e.count / max) * 100);
                            return (
                                <div key={`${e.error}-${i}`}>
                                    <div className="flex items-center justify-between text-xs mb-1">
                                        <span className="text-red-400 font-medium truncate max-w-[400px]">{e.error}</span>
                                        <span className="text-foreground font-semibold">{e.count}</span>
                                    </div>
                                    <div className="w-full h-1.5 bg-border rounded-full overflow-hidden">
                                        <div className="h-full rounded-full bg-red-500/60" style={{ width: `${pct}%` }} />
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </section>
    );
}
