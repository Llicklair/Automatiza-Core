"use client";

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
    return (
        <>
            {/* Controls */}
            <div className="flex items-center gap-3 flex-wrap">
                <div className="flex items-center gap-1 rounded-xl border border-border bg-card px-2 py-1">
                    <button onClick={() => setMonth(prevMonth(month))} className="p-1.5 rounded-lg hover:bg-accent/50 text-muted-foreground">
                        <ChevronLeft className="w-4 h-4" />
                    </button>
                    <span className="text-sm font-semibold text-foreground w-36 text-center">{fmtMonth(month)}</span>
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
                    <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} /> Actualizar
                </button>

                <button onClick={handleGenerate} disabled={generating || !isCurrentOrPast}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary hover:bg-primary text-sm font-semibold text-foreground transition-colors disabled:opacity-40">
                    {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <PlusCircle className="w-4 h-4" />}
                    Generar PDF
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
                    <CheckCircle2 className="w-4 h-4 shrink-0" /> PDF generado y guardado en documentos
                </div>
            )}

            {loading && (
                <div className="flex items-center justify-center py-20 text-muted-foreground">
                    <Loader2 className="w-6 h-6 animate-spin mr-2" /> Cargando datos del período…
                </div>
            )}

            {snap && !loading && (
                <>
                    {/* Resumen ejecutivo */}
                    <div className="rounded-2xl border border-primary/20 bg-gradient-to-br from-indigo-900/20 to-card p-5">
                        <p className="text-xs font-semibold text-primary uppercase tracking-wider mb-2">Resumen ejecutivo · {fmtMonth(snap.month)}</p>
                        <p className="text-sm text-foreground leading-relaxed">{snap.resumen_ejecutivo}</p>
                    </div>

                    {/* KPIs */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <KpiCard label="Ingresos" value={`${fmt(snap.facturas.ingresos_total)} €`} sub={`${snap.facturas.facturas_emitidas} facturas`} icon={TrendingUp} color="emerald" />
                        <KpiCard label="Gastos" value={`${fmt(snap.facturas.gastos_total)} €`} sub={`${snap.facturas.facturas_recibidas} facturas`} icon={TrendingDown} color="red" />
                        <KpiCard label="Margen bruto" value={`${fmt(snap.facturas.margen_bruto)} €`} sub={`${snap.facturas.margen_pct.toFixed(1)}% sobre ingresos`} icon={BarChart3} color={snap.facturas.margen_bruto >= 0 ? "indigo" : "red"} />
                        <KpiCard label="Pendiente cobro" value={`${fmt(snap.facturas.importe_pendiente_cobro)} €`} sub={`${snap.facturas.facturas_pendientes_cobro} facturas`} icon={Clock} color="amber" />
                    </div>

                    {/* Detail sections */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Section title="Facturación" icon={FileText}>
                            <Row label="Ingresos totales" value={`${fmt(snap.facturas.ingresos_total)} €`} />
                            <Row label="Gastos totales" value={`${fmt(snap.facturas.gastos_total)} €`} />
                            <Row label="Margen bruto" value={`${fmt(snap.facturas.margen_bruto)} €`} highlight />
                            <Row label="Facturas emitidas" value={String(snap.facturas.facturas_emitidas)} />
                            <Row label="Facturas recibidas" value={String(snap.facturas.facturas_recibidas)} />
                            <Row label="Pendientes de cobro" value={`${snap.facturas.facturas_pendientes_cobro} · ${fmt(snap.facturas.importe_pendiente_cobro)} €`} />
                        </Section>

                        <Section title="Posición bancaria" icon={Landmark}>
                            <Row label="Entradas" value={`${fmt(snap.banca.total_ingresos)} €`} />
                            <Row label="Salidas" value={`${fmt(snap.banca.total_gastos)} €`} />
                            <Row label="Saldo neto del mes" value={`${fmt(snap.banca.saldo_neto)} €`} highlight />
                            <Row label="Movimientos registrados" value={String(snap.banca.transacciones)} />
                            <Row label="Reconciliados" value={String(snap.banca.reconciliadas)} />
                        </Section>

                        <Section title="Recursos Humanos" icon={Briefcase}>
                            <Row label="Empleados activos" value={String(snap.rrhh.empleados_activos)} />
                            <Row label="Coste nóminas" value={`${fmt(snap.rrhh.coste_nominas)} €`} highlight />
                            <Row label="Nóminas pagadas" value={String(snap.rrhh.nominas_pagadas)} />
                            <Row label="Nóminas pendientes" value={String(snap.rrhh.nominas_pendientes)} />
                        </Section>

                        <Section title="Clientes" icon={Users}>
                            <Row label="Total clientes" value={String(snap.clientes.total_clientes)} />
                            <Row label="Nuevos este período" value={String(snap.clientes.nuevos_periodo)} />
                            {snap.clientes.top_client_name && (
                                <Row label="Cliente principal" value={`${snap.clientes.top_client_name} · ${fmt(snap.clientes.top_client_amount)} €`} highlight />
                            )}
                        </Section>
                    </div>
                </>
            )}

            {!loading && !snap && !error && (
                <div className="text-center py-20 text-muted-foreground">
                    <BarChart3 className="w-12 h-12 mx-auto mb-4 opacity-30" />
                    <p className="text-lg font-semibold text-muted-foreground">Sin datos para {fmtMonth(month)}</p>
                    <p className="text-sm mt-1">Prueba con otro mes o registra actividad primero</p>
                </div>
            )}
        </>
    );
}
