"use client";

import { useTranslations } from "next-intl";
import {
    BarChart3, TrendingUp, TrendingDown, Users, Briefcase,
    Landmark, FileText, RefreshCw, ChevronLeft, ChevronRight,
    Loader2, AlertCircle, CheckCircle2, Clock, PlusCircle,
} from "lucide-react";
import type { CompanySnapshot } from "@/lib/api";
import { KpiCard, Section, Row } from "./InformesHelpers";
import { fmt, fmtMonth, prevMonth, nextMonth, currentMonthStr } from "../_hooks/useInformes";

interface GestionTabProps {
    month: string;
    setMonth: (m: string) => void;
    snap: CompanySnapshot | null;
    loading: boolean;
    generating: boolean;
    error: string | null;
    genOk: boolean;
    isCurrentOrPast: boolean;
    loadSnapshot: () => void;
    handleGenerate: () => void;
}

export function GestionTab({
    month, setMonth,
    snap, loading, generating, error, genOk,
    isCurrentOrPast,
    loadSnapshot, handleGenerate,
}: GestionTabProps) {
    const t = useTranslations("informes");
    return (
        <>
            {/* Controls */}
            <div className="flex items-center gap-3 flex-wrap">
                <div className="flex items-center gap-1 rounded-xl border border-border bg-card px-2 py-1">
                    <button onClick={() => setMonth(prevMonth(month))} className="p-1.5 rounded-lg hover:bg-accent/50 text-muted-foreground">
                        <ChevronLeft className="w-4 h-4" />
                    </button>
                    <span className="text-sm font-semibold text-foreground w-36 text-center">{fmtMonth(t, month)}</span>
                    <button
                        onClick={() => setMonth(nextMonth(month))}
                        disabled={month >= currentMonthStr()}
                        className="p-1.5 rounded-lg hover:bg-accent/50 text-muted-foreground disabled:opacity-30"
                    >
                        <ChevronRight className="w-4 h-4" />
                    </button>
                </div>

                <button onClick={loadSnapshot} disabled={loading}
                    className="flex items-center gap-2 px-3 py-2 rounded-xl border border-border text-sm text-foreground hover:bg-accent/50 transition-colors">
                    <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} /> {t("gestion.refresh")}
                </button>

                <button onClick={handleGenerate} disabled={generating || !isCurrentOrPast}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary hover:bg-primary text-sm font-semibold text-foreground transition-colors disabled:opacity-40">
                    {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <PlusCircle className="w-4 h-4" />}
                    {t("gestion.generatePdf")}
                </button>
            </div>

            {/* Alerts */}
            {error && (
                <div className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
                    <AlertCircle className="w-4 h-4 shrink-0" /> {error}
                </div>
            )}
            {genOk && (
                <div className="flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
                    <CheckCircle2 className="w-4 h-4 shrink-0" /> {t("gestion.genOk")}
                </div>
            )}

            {loading && (
                <div className="flex items-center justify-center py-20 text-muted-foreground">
                    <Loader2 className="w-6 h-6 animate-spin mr-2" /> {t("gestion.loadingPeriod")}
                </div>
            )}

            {snap && !loading && (
                <>
                    {/* Resumen ejecutivo */}
                    <div className="rounded-2xl border border-primary/20 bg-gradient-to-br from-indigo-900/20 to-card p-5">
                        <p className="text-xs font-semibold text-primary uppercase tracking-wider mb-2">{t("gestion.resumenEjecutivo", { period: fmtMonth(t, snap.month) })}</p>
                        <p className="text-sm text-foreground leading-relaxed">{snap.resumen_ejecutivo}</p>
                    </div>

                    {/* KPIs */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <KpiCard label={t("gestion.kpiIngresos")} value={`${fmt(snap.facturas.ingresos_total)} €`} sub={t("gestion.facturasCount", { count: snap.facturas.facturas_emitidas })} icon={TrendingUp} color="emerald" />
                        <KpiCard label={t("gestion.kpiGastos")} value={`${fmt(snap.facturas.gastos_total)} €`} sub={t("gestion.facturasCount", { count: snap.facturas.facturas_recibidas })} icon={TrendingDown} color="red" />
                        <KpiCard label={t("gestion.kpiMargenBruto")} value={`${fmt(snap.facturas.margen_bruto)} €`} sub={t("gestion.margenSobreIngresos", { pct: snap.facturas.margen_pct.toFixed(1) })} icon={BarChart3} color={snap.facturas.margen_bruto >= 0 ? "indigo" : "red"} />
                        <KpiCard label={t("gestion.kpiPendienteCobro")} value={`${fmt(snap.facturas.importe_pendiente_cobro)} €`} sub={t("gestion.facturasCount", { count: snap.facturas.facturas_pendientes_cobro })} icon={Clock} color="amber" />
                    </div>

                    {/* Detail sections */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Section title={t("gestion.sectionFacturacion")} icon={FileText}>
                            <Row label={t("gestion.ingresosTotales")} value={`${fmt(snap.facturas.ingresos_total)} €`} />
                            <Row label={t("gestion.gastosTotales")} value={`${fmt(snap.facturas.gastos_total)} €`} />
                            <Row label={t("gestion.margenBruto")} value={`${fmt(snap.facturas.margen_bruto)} €`} highlight />
                            <Row label={t("gestion.facturasEmitidas")} value={String(snap.facturas.facturas_emitidas)} />
                            <Row label={t("gestion.facturasRecibidas")} value={String(snap.facturas.facturas_recibidas)} />
                            <Row label={t("gestion.pendientesCobro")} value={`${snap.facturas.facturas_pendientes_cobro} · ${fmt(snap.facturas.importe_pendiente_cobro)} €`} />
                        </Section>

                        <Section title={t("gestion.sectionPosicionBancaria")} icon={Landmark}>
                            <Row label={t("gestion.entradas")} value={`${fmt(snap.banca.total_ingresos)} €`} />
                            <Row label={t("gestion.salidas")} value={`${fmt(snap.banca.total_gastos)} €`} />
                            <Row label={t("gestion.saldoNetoMes")} value={`${fmt(snap.banca.saldo_neto)} €`} highlight />
                            <Row label={t("gestion.movimientosRegistrados")} value={String(snap.banca.transacciones)} />
                            <Row label={t("gestion.reconciliados")} value={String(snap.banca.reconciliadas)} />
                        </Section>

                        <Section title={t("gestion.sectionRRHH")} icon={Briefcase}>
                            <Row label={t("gestion.empleadosActivos")} value={String(snap.rrhh.empleados_activos)} />
                            <Row label={t("gestion.costeNominas")} value={`${fmt(snap.rrhh.coste_nominas)} €`} highlight />
                            <Row label={t("gestion.nominasPagadas")} value={String(snap.rrhh.nominas_pagadas)} />
                            <Row label={t("gestion.nominasPendientes")} value={String(snap.rrhh.nominas_pendientes)} />
                        </Section>

                        <Section title={t("gestion.sectionClientes")} icon={Users}>
                            <Row label={t("gestion.totalClientes")} value={String(snap.clientes.total_clientes)} />
                            <Row label={t("gestion.nuevosPeriodo")} value={String(snap.clientes.nuevos_periodo)} />
                            {snap.clientes.top_client_name && (
                                <Row label={t("gestion.clientePrincipal")} value={`${snap.clientes.top_client_name} · ${fmt(snap.clientes.top_client_amount)} €`} highlight />
                            )}
                        </Section>
                    </div>
                </>
            )}

            {!loading && !snap && !error && (
                <div className="text-center py-20 text-muted-foreground">
                    <BarChart3 className="w-12 h-12 mx-auto mb-4 opacity-30" />
                    <p className="text-lg font-semibold text-muted-foreground">{t("gestion.emptyTitle", { period: fmtMonth(t, month) })}</p>
                    <p className="text-sm mt-1">{t("gestion.emptySubtitle")}</p>
                </div>
            )}
        </>
    );
}
