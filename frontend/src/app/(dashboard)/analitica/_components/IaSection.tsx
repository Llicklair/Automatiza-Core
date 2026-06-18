"use client";

import {
    Zap, BrainCircuit, Clock, CheckCircle2, XCircle,
    Coins, Timer, Cpu, AlertCircle,
} from "lucide-react";
import { useTranslations } from "next-intl";
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
    const t = useTranslations("analitica");
    return (
        <section className="space-y-6">
            <SectionHeader icon={BrainCircuit} title={t("ia.title")} subtitle={t("ia.subtitle")} />
            {/* KPIs IA — fila 1: tasks */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                <KpiCard
                    label={t("ia.kpiTasaExito")}
                    value={`${tasksSuccessRate}%`}
                    sub={t("ia.kpiTasaExitoSub")}
                    icon={Zap}
                    color="indigo"
                />
                <KpiCard
                    label={t("ia.kpiCompletadas")}
                    value={`${tasksDone}`}
                    icon={CheckCircle2}
                    color="emerald"
                />
                <KpiCard
                    label={t("ia.kpiEnCurso")}
                    value={`${tasksPending}`}
                    icon={Clock}
                    color="amber"
                />
                <KpiCard
                    label={t("ia.kpiFallidas")}
                    value={`${tasksFailed}`}
                    icon={XCircle}
                    color="red"
                />
            </div>

            {/* KPIs IA — fila 2: cost & latency */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                <KpiCard
                    label={t("ia.kpiTokens")}
                    value={fmtInt(ia.tokens_total_periodo)}
                    sub={t("ia.kpiTokensSub", { period: periodLabel })}
                    icon={Cpu}
                    color="indigo"
                />
                <KpiCard
                    label={t("ia.kpiCoste")}
                    value={`${fmt(ia.coste_total_periodo_eur)}€`}
                    sub={t("ia.kpiCosteSub")}
                    icon={Coins}
                    color="amber"
                />
                <KpiCard
                    label={t("ia.kpiLatencia")}
                    value={`${ia.tiempo_medio_ms} ms`}
                    sub={t("ia.kpiLatenciaSub")}
                    icon={Timer}
                    color="emerald"
                />
            </div>

            {/* Desglose por agente */}
            <div className="bg-card border border-border rounded-2xl p-6">
                <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                    <BrainCircuit className="w-4 h-4 text-primary" /> {t("ia.rendimientoTitle")}
                </h2>
                <p className="text-xs text-muted-foreground mb-5">{t("ia.rendimientoSubtitle", { period: periodLabel })}</p>
                {iaDetalle.por_agente.length === 0 ? (
                    <div className="h-[140px] flex items-center justify-center text-sm text-muted-foreground">
                        {t("ia.rendimientoEmpty")}
                    </div>
                ) : (
                    <div className="overflow-x-auto rounded-xl border border-border">
                        <table className="w-full text-xs">
                            <thead className="bg-muted">
                                <tr>
                                    <th className="text-left py-2 px-3 text-muted-foreground font-medium">{t("ia.colAgente")}</th>
                                    <th className="text-right py-2 px-3 text-muted-foreground font-medium">{t("ia.colEjec")}</th>
                                    <th className="text-right py-2 px-3 text-muted-foreground font-medium">{t("ia.colExito")}</th>
                                    <th className="text-right py-2 px-3 text-muted-foreground font-medium">{t("ia.colTokens")}</th>
                                    <th className="text-right py-2 px-3 text-muted-foreground font-medium">{t("ia.colCoste")}</th>
                                    <th className="text-right py-2 px-3 text-muted-foreground font-medium">{t("ia.colLatencia")}</th>
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
                    <AlertCircle className="w-4 h-4 text-red-400" /> {t("ia.erroresTitle")}
                </h2>
                <p className="text-xs text-muted-foreground mb-5">{t("ia.erroresSubtitle")}</p>
                {iaDetalle.top_errores.length === 0 ? (
                    <div className="h-[100px] flex items-center justify-center text-sm text-muted-foreground">
                        {t("ia.erroresEmpty")}
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
