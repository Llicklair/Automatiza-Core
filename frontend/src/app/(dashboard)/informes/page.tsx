"use client";

import { useEffect, useState } from "react";
import { api, type CompanySnapshot, type FiscalSnapshot, type ReportDoc } from "@/lib/api";
import {
    BarChart3, TrendingUp, TrendingDown, Users, Briefcase,
    Landmark, FileText, Download, RefreshCw, ChevronLeft, ChevronRight,
    Loader2, AlertCircle, CheckCircle2, Clock, PlusCircle,
    Receipt, Building2, Scale, Trash2
} from "lucide-react";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmt(n: number) {
    return n.toLocaleString("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtMonth(m: string) {
    const [y, mo] = m.split("-");
    const months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
    return `${months[parseInt(mo) - 1]} ${y}`;
}

function prevMonth(m: string) {
    const [y, mo] = m.split("-").map(Number);
    const d = new Date(y, mo - 2, 1);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function nextMonth(m: string) {
    const [y, mo] = m.split("-").map(Number);
    const d = new Date(y, mo, 1);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function currentMonthStr() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function currentQuarterStr() {
    const d = new Date();
    const q = Math.ceil((d.getMonth() + 1) / 3);
    return `${d.getFullYear()}-Q${q}`;
}

function fmtQuarter(q: string) {
    const [y, qn] = q.split("-Q");
    return `T${qn} ${y}`;
}

function prevQuarter(q: string) {
    const [y, qn] = q.split("-Q").map(Number);
    if (qn === 1) return `${y - 1}-Q4`;
    return `${y}-Q${qn - 1}`;
}

function nextQuarter(q: string) {
    const [y, qn] = q.split("-Q").map(Number);
    if (qn === 4) return `${y + 1}-Q1`;
    return `${y}-Q${qn + 1}`;
}

// ─── KPI Card ─────────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, icon: Icon, color = "indigo" }: {
    label: string; value: string; sub?: string; icon: any;
    color?: "indigo" | "emerald" | "red" | "amber" | "blue" | "purple";
}) {
    const cls: Record<string, string> = {
        indigo: "border-indigo-500/20 bg-indigo-500/10 text-indigo-400",
        emerald: "border-emerald-500/20 bg-emerald-500/10 text-emerald-400",
        red: "border-red-500/20 bg-red-500/10 text-red-400",
        amber: "border-amber-500/20 bg-amber-500/10 text-amber-400",
        blue: "border-blue-500/20 bg-blue-500/10 text-blue-400",
        purple: "border-purple-500/20 bg-purple-500/10 text-purple-400",
    };
    const c = cls[color];
    return (
        <div className="rounded-2xl border border-white/5 bg-[#111113] p-5 flex flex-col gap-3">
            <div className="flex items-center gap-3">
                <div className={`w-9 h-9 rounded-xl border ${c} flex items-center justify-center shrink-0`}>
                    <Icon className={`w-4 h-4 ${c.split(" ")[2]}`} />
                </div>
                <span className="text-xs text-zinc-400 font-medium">{label}</span>
            </div>
            <div>
                <p className="text-xl font-bold text-white">{value}</p>
                {sub && <p className="text-xs text-zinc-500 mt-0.5">{sub}</p>}
            </div>
        </div>
    );
}

// ─── Section ──────────────────────────────────────────────────────────────────

function Section({ title, icon: Icon, children }: { title: string; icon: any; children: React.ReactNode }) {
    return (
        <div className="rounded-2xl border border-white/5 bg-[#111113] overflow-hidden">
            <div className="flex items-center gap-2 px-5 py-3 border-b border-white/5">
                <Icon className="w-4 h-4 text-zinc-400" />
                <span className="text-sm font-semibold text-zinc-200">{title}</span>
            </div>
            <div className="p-5">{children}</div>
        </div>
    );
}

function Row({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
    return (
        <div className={`flex justify-between py-2 border-b border-white/5 last:border-0 ${highlight ? "text-white" : "text-zinc-400"}`}>
            <span className="text-sm">{label}</span>
            <span className={`text-sm font-semibold ${highlight ? "text-white" : "text-zinc-200"}`}>{value}</span>
        </div>
    );
}

// ─── Tab Button ───────────────────────────────────────────────────────────────

function TabBtn({ active, label, icon: Icon, onClick }: {
    active: boolean; label: string; icon: any; onClick: () => void;
}) {
    return (
        <button
            onClick={onClick}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-colors ${
                active
                    ? "bg-white/10 text-white"
                    : "text-zinc-500 hover:text-zinc-300 hover:bg-white/5"
            }`}
        >
            <Icon className="w-4 h-4" />
            {label}
        </button>
    );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function InformesPage() {
    const [tab, setTab] = useState<"gestion" | "fiscal">("gestion");

    // ── Gestión state ──
    const [month, setMonth] = useState(currentMonthStr());
    const [snap, setSnap] = useState<CompanySnapshot | null>(null);
    const [loading, setLoading] = useState(false);
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [genOk, setGenOk] = useState(false);

    // ── Fiscal state ──
    const [fiscalMode, setFiscalMode] = useState<"mensual" | "trimestral">("trimestral");
    const [fiscalMonth, setFiscalMonth] = useState(currentMonthStr());
    const [fiscalQuarter, setFiscalQuarter] = useState(currentQuarterStr());
    const [fiscalSnap, setFiscalSnap] = useState<FiscalSnapshot | null>(null);
    const [fiscalLoading, setFiscalLoading] = useState(false);
    const [fiscalGenerating, setFiscalGenerating] = useState(false);
    const [fiscalError, setFiscalError] = useState<string | null>(null);
    const [fiscalGenOk, setFiscalGenOk] = useState(false);

    // ── Shared state ──
    const [reports, setReports] = useState<ReportDoc[]>([]);

    // ── Gestión loaders ──
    async function loadSnapshot() {
        setLoading(true);
        setError(null);
        try {
            const data = await api.reports.snapshot(month);
            setSnap(data);
        } catch (e: any) {
            setError(e.message || "Error cargando datos");
        } finally {
            setLoading(false);
        }
    }

    async function loadReports() {
        try {
            const data = await api.reports.list();
            setReports(data);
        } catch { }
    }

    async function handleGenerate() {
        setGenerating(true);
        setGenOk(false);
        setError("");
        try {
            await api.reports.generate(month);
            setGenOk(true);
            await loadReports();
        } catch (e: any) {
            const msg = e?.message || "Error desconocido";
            setError(`Error generando informe: ${msg}`);
            console.error("[informes] generate error:", e);
        } finally {
            setGenerating(false);
        }
    }

    // ── Fiscal loaders ──
    const fiscalPeriod = fiscalMode === "trimestral" ? fiscalQuarter : fiscalMonth;

    async function loadFiscalSnapshot() {
        setFiscalLoading(true);
        setFiscalError(null);
        try {
            const data = await api.reports.fiscalSnapshot(fiscalPeriod);
            setFiscalSnap(data);
        } catch (e: any) {
            setFiscalError(e.message || "Error cargando datos fiscales");
        } finally {
            setFiscalLoading(false);
        }
    }

    async function handleGenerateFiscal() {
        setFiscalGenerating(true);
        setFiscalGenOk(false);
        setFiscalError("");
        try {
            await api.reports.generateFiscal(fiscalPeriod);
            setFiscalGenOk(true);
            await loadReports();
        } catch (e: any) {
            const msg = e?.message || "Error desconocido";
            setFiscalError(`Error generando informe fiscal: ${msg}`);
            console.error("[informes] fiscal generate error:", e);
        } finally {
            setFiscalGenerating(false);
        }
    }

    // ── Download ──
    async function handleDownload(id: string, fileName: string) {
        setError("");
        setFiscalError("");
        try {
            await api.reports.download(id, fileName);
        } catch (e: any) {
            const msg = e?.message || "Error desconocido";
            const setErr = tab === "fiscal" ? setFiscalError : setError;
            setErr(`Error descargando: ${msg}`);
        }
    }

    async function handleDeleteReport(id: string) {
        if (!confirm("¿Eliminar este informe? Esta acción no se puede deshacer.")) return;
        try {
            await api.reports.delete(id);
            setReports(prev => prev.filter(r => r.id !== id));
        } catch (e: any) {
            const setErr = tab === "fiscal" ? setFiscalError : setError;
            setErr(`Error eliminando: ${e?.message || "Error desconocido"}`);
        }
    }

    // ── Effects ──
    // eslint-disable-next-line react-hooks/exhaustive-deps
    useEffect(() => { if (tab === "gestion") loadSnapshot(); }, [month, tab]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    useEffect(() => { if (tab === "fiscal") loadFiscalSnapshot(); }, [fiscalPeriod, tab]);
    useEffect(() => { loadReports(); }, []);

    const isCurrentOrPast = month <= currentMonthStr();

    return (
        <div className="p-6 max-w-6xl mx-auto space-y-6">

            {/* Header + Tabs */}
            <div className="flex items-center justify-between gap-4 flex-wrap">
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                        <BarChart3 className="w-6 h-6 text-indigo-400" />
                        Informes IA
                    </h1>
                    <p className="text-sm text-zinc-400 mt-0.5">Informes generados automáticamente por IA</p>
                </div>

                <div className="flex items-center gap-1 rounded-xl border border-white/10 bg-[#111113] p-1">
                    <TabBtn active={tab === "gestion"} label="Gestión" icon={BarChart3} onClick={() => setTab("gestion")} />
                    <TabBtn active={tab === "fiscal"} label="Fiscal" icon={Receipt} onClick={() => setTab("fiscal")} />
                </div>
            </div>

            {/* ════════════════════════════════════════════════════════════════ */}
            {/* TAB: GESTIÓN */}
            {/* ════════════════════════════════════════════════════════════════ */}
            {tab === "gestion" && (
                <>
                    {/* Controls */}
                    <div className="flex items-center gap-3 flex-wrap">
                        <div className="flex items-center gap-1 rounded-xl border border-white/10 bg-[#111113] px-2 py-1">
                            <button onClick={() => setMonth(prevMonth(month))} className="p-1.5 rounded-lg hover:bg-white/5 text-zinc-400">
                                <ChevronLeft className="w-4 h-4" />
                            </button>
                            <span className="text-sm font-semibold text-white w-36 text-center">{fmtMonth(month)}</span>
                            <button
                                onClick={() => setMonth(nextMonth(month))}
                                disabled={month >= currentMonthStr()}
                                className="p-1.5 rounded-lg hover:bg-white/5 text-zinc-400 disabled:opacity-30"
                            >
                                <ChevronRight className="w-4 h-4" />
                            </button>
                        </div>

                        <button onClick={loadSnapshot} disabled={loading}
                            className="flex items-center gap-2 px-3 py-2 rounded-xl border border-white/10 text-sm text-zinc-300 hover:bg-white/5 transition-colors">
                            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} /> Actualizar
                        </button>

                        <button onClick={handleGenerate} disabled={generating || !isCurrentOrPast}
                            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-sm font-semibold text-white transition-colors disabled:opacity-40">
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
                        <div className="flex items-center justify-center py-20 text-zinc-500">
                            <Loader2 className="w-6 h-6 animate-spin mr-2" /> Cargando datos del período…
                        </div>
                    )}

                    {snap && !loading && (
                        <>
                            {/* Resumen ejecutivo */}
                            <div className="rounded-2xl border border-indigo-500/20 bg-gradient-to-br from-indigo-900/20 to-[#111113] p-5">
                                <p className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-2">Resumen ejecutivo · {fmtMonth(snap.month)}</p>
                                <p className="text-sm text-zinc-300 leading-relaxed">{snap.resumen_ejecutivo}</p>
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
                        <div className="text-center py-20 text-zinc-500">
                            <BarChart3 className="w-12 h-12 mx-auto mb-4 opacity-30" />
                            <p className="text-lg font-semibold text-zinc-400">Sin datos para {fmtMonth(month)}</p>
                            <p className="text-sm mt-1">Prueba con otro mes o registra actividad primero</p>
                        </div>
                    )}
                </>
            )}

            {/* ════════════════════════════════════════════════════════════════ */}
            {/* TAB: FISCAL */}
            {/* ════════════════════════════════════════════════════════════════ */}
            {tab === "fiscal" && (
                <>
                    {/* Controls */}
                    <div className="flex items-center gap-3 flex-wrap">
                        {/* Mode toggle */}
                        <div className="flex items-center gap-0 rounded-xl border border-white/10 bg-[#111113] p-0.5">
                            <button onClick={() => setFiscalMode("mensual")}
                                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${fiscalMode === "mensual" ? "bg-white/10 text-white" : "text-zinc-500 hover:text-zinc-300"}`}>
                                Mensual
                            </button>
                            <button onClick={() => setFiscalMode("trimestral")}
                                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${fiscalMode === "trimestral" ? "bg-white/10 text-white" : "text-zinc-500 hover:text-zinc-300"}`}>
                                Trimestral
                            </button>
                        </div>

                        {/* Period selector */}
                        {fiscalMode === "mensual" ? (
                            <div className="flex items-center gap-1 rounded-xl border border-white/10 bg-[#111113] px-2 py-1">
                                <button onClick={() => setFiscalMonth(prevMonth(fiscalMonth))} className="p-1.5 rounded-lg hover:bg-white/5 text-zinc-400">
                                    <ChevronLeft className="w-4 h-4" />
                                </button>
                                <span className="text-sm font-semibold text-white w-36 text-center">{fmtMonth(fiscalMonth)}</span>
                                <button onClick={() => setFiscalMonth(nextMonth(fiscalMonth))}
                                    disabled={fiscalMonth >= currentMonthStr()}
                                    className="p-1.5 rounded-lg hover:bg-white/5 text-zinc-400 disabled:opacity-30">
                                    <ChevronRight className="w-4 h-4" />
                                </button>
                            </div>
                        ) : (
                            <div className="flex items-center gap-1 rounded-xl border border-white/10 bg-[#111113] px-2 py-1">
                                <button onClick={() => setFiscalQuarter(prevQuarter(fiscalQuarter))} className="p-1.5 rounded-lg hover:bg-white/5 text-zinc-400">
                                    <ChevronLeft className="w-4 h-4" />
                                </button>
                                <span className="text-sm font-semibold text-white w-36 text-center">{fmtQuarter(fiscalQuarter)}</span>
                                <button onClick={() => setFiscalQuarter(nextQuarter(fiscalQuarter))}
                                    disabled={fiscalQuarter >= currentQuarterStr()}
                                    className="p-1.5 rounded-lg hover:bg-white/5 text-zinc-400 disabled:opacity-30">
                                    <ChevronRight className="w-4 h-4" />
                                </button>
                            </div>
                        )}

                        <button onClick={loadFiscalSnapshot} disabled={fiscalLoading}
                            className="flex items-center gap-2 px-3 py-2 rounded-xl border border-white/10 text-sm text-zinc-300 hover:bg-white/5 transition-colors">
                            <RefreshCw className={`w-4 h-4 ${fiscalLoading ? "animate-spin" : ""}`} /> Actualizar
                        </button>

                        <button onClick={handleGenerateFiscal} disabled={fiscalGenerating}
                            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-sm font-semibold text-white transition-colors disabled:opacity-40">
                            {fiscalGenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <PlusCircle className="w-4 h-4" />}
                            Generar PDF Fiscal
                        </button>
                    </div>

                    {/* Alerts */}
                    {fiscalError && (
                        <div className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
                            <AlertCircle className="w-4 h-4 shrink-0" /> {fiscalError}
                        </div>
                    )}
                    {fiscalGenOk && (
                        <div className="flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
                            <CheckCircle2 className="w-4 h-4 shrink-0" /> PDF fiscal generado y guardado
                        </div>
                    )}

                    {fiscalLoading && (
                        <div className="flex items-center justify-center py-20 text-zinc-500">
                            <Loader2 className="w-6 h-6 animate-spin mr-2" /> Cargando datos fiscales…
                        </div>
                    )}

                    {fiscalSnap && !fiscalLoading && (
                        <>
                            {/* Resumen ejecutivo */}
                            <div className="rounded-2xl border border-red-500/20 bg-gradient-to-br from-red-900/20 to-[#111113] p-5">
                                <p className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-2">
                                    Resumen fiscal · {fiscalSnap.period_label}
                                </p>
                                <p className="text-sm text-zinc-300 leading-relaxed">{fiscalSnap.resumen_ejecutivo}</p>
                            </div>

                            {/* KPIs */}
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <KpiCard
                                    label="Resultado IVA"
                                    value={`${fmt(fiscalSnap.iva.resultado_iva)} €`}
                                    sub={fiscalSnap.iva.resultado_iva > 0 ? "A ingresar" : "A compensar"}
                                    icon={Receipt}
                                    color={fiscalSnap.iva.resultado_iva > 0 ? "red" : "emerald"}
                                />
                                <KpiCard
                                    label="IRPF Retenciones"
                                    value={`${fmt(fiscalSnap.irpf.total_retenciones)} €`}
                                    sub="Retenciones del periodo"
                                    icon={Users}
                                    color="amber"
                                />
                                <KpiCard
                                    label="IS Estimado"
                                    value={`${fmt(fiscalSnap.impuesto_sociedades.cuota_estimada)} €`}
                                    sub={`Tipo ${fiscalSnap.impuesto_sociedades.tipo_estimado}%`}
                                    icon={Building2}
                                    color="blue"
                                />
                                <KpiCard
                                    label="Total obligaciones"
                                    value={`${fmt(fiscalSnap.iva.resultado_iva + fiscalSnap.irpf.total_retenciones + fiscalSnap.impuesto_sociedades.cuota_estimada)} €`}
                                    sub="Estimación total"
                                    icon={Scale}
                                    color="indigo"
                                />
                            </div>

                            {/* Detail sections */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {/* IVA */}
                                <Section title="IVA — Repercutido vs Soportado" icon={Receipt}>
                                    <Row label="IVA Repercutido (21%)" value={`${fmt(fiscalSnap.iva.repercutido_21)} €`} />
                                    <Row label="IVA Repercutido (10%)" value={`${fmt(fiscalSnap.iva.repercutido_10)} €`} />
                                    <Row label="IVA Repercutido (4%)" value={`${fmt(fiscalSnap.iva.repercutido_4)} €`} />
                                    <Row label="Total repercutido" value={`${fmt(fiscalSnap.iva.total_repercutido)} €`} highlight />
                                    <div className="border-t border-white/5 mt-1 pt-1" />
                                    <Row label="IVA Soportado (21%)" value={`${fmt(fiscalSnap.iva.soportado_21)} €`} />
                                    <Row label="IVA Soportado (10%)" value={`${fmt(fiscalSnap.iva.soportado_10)} €`} />
                                    <Row label="IVA Soportado (4%)" value={`${fmt(fiscalSnap.iva.soportado_4)} €`} />
                                    <Row label="Total soportado" value={`${fmt(fiscalSnap.iva.total_soportado)} €`} highlight />
                                    <div className="border-t border-white/10 mt-1 pt-1" />
                                    <Row label="Resultado IVA" value={`${fmt(fiscalSnap.iva.resultado_iva)} €`} highlight />
                                </Section>

                                {/* IRPF + IS */}
                                <div className="space-y-4">
                                    <Section title="Retenciones IRPF" icon={Users}>
                                        <Row label="Retenciones nóminas" value={`${fmt(fiscalSnap.irpf.retenciones_nominas)} €`} />
                                        <Row label="Retenciones facturas" value={`${fmt(fiscalSnap.irpf.retenciones_facturas)} €`} />
                                        <Row label="Total retenciones" value={`${fmt(fiscalSnap.irpf.total_retenciones)} €`} highlight />
                                    </Section>

                                    <Section title="Impuesto de Sociedades (est.)" icon={Building2}>
                                        <Row label="Ingresos brutos" value={`${fmt(fiscalSnap.impuesto_sociedades.ingresos_brutos)} €`} />
                                        <Row label="Gastos deducibles" value={`${fmt(fiscalSnap.impuesto_sociedades.gastos_deducibles)} €`} />
                                        <Row label="Base imponible" value={`${fmt(fiscalSnap.impuesto_sociedades.base_imponible)} €`} highlight />
                                        <Row label={`Tipo impositivo`} value={`${fiscalSnap.impuesto_sociedades.tipo_estimado}%`} />
                                        <Row label="Cuota estimada" value={`${fmt(fiscalSnap.impuesto_sociedades.cuota_estimada)} €`} highlight />
                                    </Section>
                                </div>
                            </div>

                            {/* Disclaimer */}
                            <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-xs text-amber-300/80 text-center">
                                Estimación orientativa generada automáticamente. No sustituye el asesoramiento fiscal profesional ni las declaraciones ante la AEAT.
                            </div>
                        </>
                    )}

                    {!fiscalLoading && !fiscalSnap && !fiscalError && (
                        <div className="text-center py-20 text-zinc-500">
                            <Receipt className="w-12 h-12 mx-auto mb-4 opacity-30" />
                            <p className="text-lg font-semibold text-zinc-400">Sin datos fiscales para {fiscalMode === "trimestral" ? fmtQuarter(fiscalQuarter) : fmtMonth(fiscalMonth)}</p>
                            <p className="text-sm mt-1">Prueba con otro periodo o registra actividad primero</p>
                        </div>
                    )}
                </>
            )}

            {/* ════════════════════════════════════════════════════════════════ */}
            {/* INFORMES GENERADOS (compartido) */}
            {/* ════════════════════════════════════════════════════════════════ */}
            {reports.length > 0 && (
                <Section title="Informes PDF generados" icon={FileText}>
                    <div className="space-y-2">
                        {reports.map(r => (
                            <div key={r.id} className="flex items-center justify-between py-2 border-b border-white/5 last:border-0 gap-3">
                                <div className="flex items-center gap-3 min-w-0">
                                    <FileText className="w-4 h-4 text-zinc-500 shrink-0" />
                                    <div className="min-w-0">
                                        <p className="text-sm text-zinc-200 truncate">{r.file_name}</p>
                                        <p className="text-xs text-zinc-500">{new Date(r.created_at).toLocaleDateString("es-ES")} · {(r.file_size / 1024).toFixed(0)} KB</p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2 shrink-0">
                                <button
                                    onClick={() => handleDownload(r.id, r.file_name)}
                                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/10 text-xs text-zinc-300 hover:bg-white/5 transition-colors"
                                >
                                    <Download className="w-3.5 h-3.5" /> Descargar
                                </button>
                                <button
                                    onClick={() => handleDeleteReport(r.id)}
                                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-red-500/20 text-xs text-red-400 hover:bg-red-500/10 transition-colors"
                                >
                                    <Trash2 className="w-3.5 h-3.5" />
                                </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </Section>
            )}
        </div>
    );
}
