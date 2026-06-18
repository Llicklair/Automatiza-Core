"use client";

import {
    TrendingDown, Clock, Activity, Wallet, Timer,
} from "lucide-react";
import { useTranslations } from "next-intl";
import type { AnalyticsDashboard } from "@/lib/api";
import { KpiCard } from "./KpiCard";
import { SectionHeader } from "./SectionHeader";
import { AgingTable } from "./AgingTable";
import { fmt, fmtInt } from "./utils";

interface FinanzasSectionProps {
    periodLabel: string;
    banca: AnalyticsDashboard["banca"];
    cobrosPagos: AnalyticsDashboard["cobros_pagos"];
    beneficioPeriodo: number;
    margenPeriodo: number;
    gastosPeriodo: number;
    recibidasCount: number;
    importePendienteCobro: number;
    importePendientePago: number;
}

export function FinanzasSection({
    periodLabel, banca, cobrosPagos,
    beneficioPeriodo, margenPeriodo, gastosPeriodo, recibidasCount,
    importePendienteCobro, importePendientePago,
}: FinanzasSectionProps) {
    const t = useTranslations("analitica");
    return (
        <section className="space-y-6">
            <SectionHeader icon={Wallet} title={t("finanzas.title")} subtitle={t("finanzas.subtitle")} />
            {/* KPIs finanzas */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-5">
                <KpiCard
                    label={t("finanzas.kpiBeneficio")}
                    value={`${fmt(beneficioPeriodo)}€`}
                    sub={t("finanzas.kpiBeneficioSub", { margin: margenPeriodo })}
                    icon={Activity}
                    color="indigo"
                />
                <KpiCard
                    label={t("finanzas.kpiGastos", { period: periodLabel })}
                    value={`${fmt(gastosPeriodo)}€`}
                    sub={t("finanzas.kpiGastosSub", { count: recibidasCount })}
                    icon={TrendingDown}
                    color="red"
                />
                <KpiCard
                    label={t("finanzas.kpiSaldo")}
                    value={`${fmt(banca.saldo_actual)}€`}
                    sub={t("finanzas.kpiSaldoSub", { count: banca.transacciones_periodo })}
                    icon={Wallet}
                    color="emerald"
                />
                <KpiCard
                    label={t("finanzas.kpiDso")}
                    value={`${cobrosPagos.dso_dias}`}
                    sub={t("finanzas.kpiDsoSub", { amount: fmt(importePendienteCobro) })}
                    icon={Clock}
                    color="amber"
                />
                <KpiCard
                    label={t("finanzas.kpiDpo")}
                    value={`${cobrosPagos.dpo_dias}`}
                    sub={t("finanzas.kpiDpoSub", { amount: fmt(importePendientePago) })}
                    icon={Timer}
                    color="indigo"
                />
            </div>

            {/* Aging cobros y pagos */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <AgingTable
                    title={t("finanzas.agingCobrosTitle")}
                    subtitle={t("finanzas.agingCobrosSubtitle")}
                    buckets={cobrosPagos.aging_cobros}
                    color="emerald"
                />
                <AgingTable
                    title={t("finanzas.agingPagosTitle")}
                    subtitle={t("finanzas.agingPagosSubtitle")}
                    buckets={cobrosPagos.aging_pagos}
                    color="red"
                />
            </div>

            {/* Banca */}
            <div className="bg-card border border-border rounded-2xl p-6">
                <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                    <Wallet className="w-4 h-4 text-primary" /> {t("finanzas.bancaTitle")}
                </h2>
                <p className="text-xs text-muted-foreground mb-5">
                    {t("finanzas.bancaSubtitle", { period: periodLabel })}
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
                    <div>
                        <p className="text-xs text-muted-foreground uppercase tracking-wide">{t("finanzas.bancaSaldo")}</p>
                        <p className="text-2xl font-bold text-foreground mt-1">{fmt(banca.saldo_actual)}€</p>
                    </div>
                    <div>
                        <p className="text-xs text-muted-foreground uppercase tracking-wide">{t("finanzas.bancaMovimientos")}</p>
                        <p className="text-2xl font-bold text-foreground mt-1">{fmtInt(banca.transacciones_periodo)}</p>
                    </div>
                    <div>
                        <p className="text-xs text-emerald-400 uppercase tracking-wide">{t("finanzas.bancaEntradas")}</p>
                        <p className="text-2xl font-semibold text-emerald-400 mt-1">+{fmt(banca.entradas_periodo)}€</p>
                    </div>
                    <div>
                        <p className="text-xs text-red-400 uppercase tracking-wide">{t("finanzas.bancaSalidas")}</p>
                        <p className="text-2xl font-semibold text-red-400 mt-1">−{fmt(banca.salidas_periodo)}€</p>
                    </div>
                </div>
                <div className="flex items-center justify-between pt-4 mt-4 border-t border-border text-xs">
                    <span className="text-muted-foreground">{t("finanzas.bancaReconciliacion")}</span>
                    <span className="text-foreground font-medium">
                        {t("finanzas.bancaConciliadas", { reconciled: banca.reconciliadas, total: banca.transacciones_periodo })}
                        {banca.pendientes_conciliar > 0 && (
                            <span className="text-amber-400 ml-2">{t("finanzas.bancaPendientes", { count: banca.pendientes_conciliar })}</span>
                        )}
                    </span>
                </div>
            </div>
        </section>
    );
}
