"use client";

import {
    TrendingDown, Clock, Activity, Wallet, Timer,
} from "lucide-react";
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
    return (
        <section className="space-y-6">
            <SectionHeader icon={Wallet} title="Finanzas" subtitle="Cobros, pagos, banca y rotación de caja" />
            {/* KPIs finanzas */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-5">
                <KpiCard
                    label="Beneficio del periodo"
                    value={`${fmt(beneficioPeriodo)}€`}
                    sub={`Margen: ${margenPeriodo}%`}
                    icon={Activity}
                    color="indigo"
                />
                <KpiCard
                    label={`Gastos · ${periodLabel}`}
                    value={`${fmt(gastosPeriodo)}€`}
                    sub={`${recibidasCount} facturas recibidas`}
                    icon={TrendingDown}
                    color="red"
                />
                <KpiCard
                    label="Saldo bancario"
                    value={`${fmt(banca.saldo_actual)}€`}
                    sub={`${banca.transacciones_periodo} movimientos`}
                    icon={Wallet}
                    color="emerald"
                />
                <KpiCard
                    label="DSO (días de cobro)"
                    value={`${cobrosPagos.dso_dias}`}
                    sub={`${fmt(importePendienteCobro)}€ pendientes`}
                    icon={Clock}
                    color="amber"
                />
                <KpiCard
                    label="DPO (días de pago)"
                    value={`${cobrosPagos.dpo_dias}`}
                    sub={`${fmt(importePendientePago)}€ por pagar`}
                    icon={Timer}
                    color="indigo"
                />
            </div>

            {/* Aging cobros y pagos */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <AgingTable
                    title="Aging de cobros"
                    subtitle="Facturas emitidas pendientes por antigüedad"
                    buckets={cobrosPagos.aging_cobros}
                    color="emerald"
                />
                <AgingTable
                    title="Aging de pagos"
                    subtitle="Facturas recibidas pendientes por antigüedad"
                    buckets={cobrosPagos.aging_pagos}
                    color="red"
                />
            </div>

            {/* Banca */}
            <div className="bg-card border border-border rounded-2xl p-6">
                <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                    <Wallet className="w-4 h-4 text-primary" /> Banca
                </h2>
                <p className="text-xs text-muted-foreground mb-5">
                    Movimientos reales de {periodLabel} (excluye demo)
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
                    <div>
                        <p className="text-xs text-muted-foreground uppercase tracking-wide">Saldo actual</p>
                        <p className="text-2xl font-bold text-foreground mt-1">{fmt(banca.saldo_actual)}€</p>
                    </div>
                    <div>
                        <p className="text-xs text-muted-foreground uppercase tracking-wide">Movimientos</p>
                        <p className="text-2xl font-bold text-foreground mt-1">{fmtInt(banca.transacciones_periodo)}</p>
                    </div>
                    <div>
                        <p className="text-xs text-emerald-400 uppercase tracking-wide">Entradas</p>
                        <p className="text-2xl font-semibold text-emerald-400 mt-1">+{fmt(banca.entradas_periodo)}€</p>
                    </div>
                    <div>
                        <p className="text-xs text-red-400 uppercase tracking-wide">Salidas</p>
                        <p className="text-2xl font-semibold text-red-400 mt-1">−{fmt(banca.salidas_periodo)}€</p>
                    </div>
                </div>
                <div className="flex items-center justify-between pt-4 mt-4 border-t border-border text-xs">
                    <span className="text-muted-foreground">Reconciliación</span>
                    <span className="text-foreground font-medium">
                        {banca.reconciliadas} / {banca.transacciones_periodo} conciliadas
                        {banca.pendientes_conciliar > 0 && (
                            <span className="text-amber-400 ml-2">({banca.pendientes_conciliar} pendientes)</span>
                        )}
                    </span>
                </div>
            </div>
        </section>
    );
}
