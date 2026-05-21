"use client";

import {
    TrendingUp, TrendingDown, FileText, Users, Zap,
    ArrowUp, ArrowDown, BrainCircuit, Clock, CheckCircle2,
    XCircle, Activity, AlertTriangle, Wallet, Briefcase,
    Package, Percent, CalendarDays, Building2, Plane, Coins,
    Timer, Cpu, AlertCircle,
    type LucideIcon
} from "lucide-react";
import {
    AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
    XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer, Legend
} from "recharts";
import { useAnalitica } from "./_hooks/useAnalitica";

interface TooltipPayloadEntry {
    value: number;
    name: string;
    color: string;
}

function fmt(n: number) {
    return n.toLocaleString("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtInt(n: number) {
    return n.toLocaleString("es-ES");
}

function monthOptions(): { value: string; label: string }[] {
    const months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
    const opts: { value: string; label: string }[] = [];
    const now = new Date();
    let y = now.getFullYear();
    let m = now.getMonth();
    for (let i = 0; i < 12; i++) {
        const value = `${y}-${String(m + 1).padStart(2, "0")}`;
        opts.push({ value, label: `${months[m]} ${y}` });
        m -= 1;
        if (m < 0) { m = 11; y -= 1; }
    }
    return opts;
}

function KpiCard({
    label, value, sub, icon: Icon, trend, color = "indigo"
}: {
    label: string; value: string; sub?: string; icon: LucideIcon;
    trend?: { dir: "up" | "down"; pct: number }; color?: "indigo" | "emerald" | "red" | "amber";
}) {
    const colors = {
        indigo: "border-primary/20 from-indigo-900/20 text-primary bg-primary/10",
        emerald: "border-emerald-500/20 from-emerald-900/20 text-emerald-400 bg-emerald-500/10",
        red: "border-red-500/20 from-red-900/20 text-red-400 bg-red-500/10",
        amber: "border-amber-500/20 from-amber-900/20 text-amber-400 bg-amber-500/10",
    };
    const c = colors[color];
    return (
        <div className={`rounded-2xl border ${c.split(" ")[0]} bg-gradient-to-br from-card ${c.split(" ")[1]} p-6 relative overflow-hidden group`}>
            <div className={`absolute -right-4 -top-4 w-24 h-24 ${c.split(" ")[3]}/30 rounded-full blur-2xl group-hover:scale-110 transition-transform duration-700`} />
            <div className="flex items-start justify-between mb-4 relative">
                <div className={`w-10 h-10 rounded-xl ${c.split(" ")[3]} border ${c.split(" ")[0]} flex items-center justify-center`}>
                    <Icon className={`w-5 h-5 ${c.split(" ")[2]}`} />
                </div>
                {trend && (
                    <span className={`flex items-center gap-1 text-xs font-bold px-2 py-1 rounded-full ${trend.dir === "up"
                        ? "bg-emerald-500/10 text-emerald-400"
                        : "bg-red-500/10 text-red-400"
                        }`}>
                        {trend.dir === "up" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />}
                        {trend.pct}%
                    </span>
                )}
            </div>
            <p className="text-xs text-muted-foreground mb-1 font-medium uppercase tracking-wide">{label}</p>
            <p className="text-3xl font-bold text-foreground tracking-tight">{value}</p>
            {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
        </div>
    );
}

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: TooltipPayloadEntry[]; label?: string }) => {
    if (active && payload?.length) {
        return (
            <div className="bg-card border border-border rounded-xl p-3 text-xs shadow-xl">
                <p className="text-muted-foreground mb-2 font-medium">{label}</p>
                {payload.map((p) => (
                    <p key={p.name} style={{ color: p.color }} className="font-semibold">
                        {p.name}: {fmt(p.value)}€
                    </p>
                ))}
            </div>
        );
    }
    return null;
};

const COLORS_PIE = ["#10b981", "#f59e0b", "#71717a", "#ef4444", "#6366f1", "#06b6d4"];

function SectionHeader({ icon: Icon, title, subtitle }: { icon: LucideIcon; title: string; subtitle?: string }) {
    return (
        <div className="flex items-center gap-3 pb-3 border-b border-border">
            <div className="w-9 h-9 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center">
                <Icon className="w-4.5 h-4.5 text-primary" />
            </div>
            <div>
                <h2 className="text-xl font-bold text-foreground tracking-tight">{title}</h2>
                {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
            </div>
        </div>
    );
}

const AGING_LABELS: { key: keyof import("@/lib/api").AnalyticsAgingBuckets; label: string; bad?: boolean }[] = [
    { key: "vencido_90", label: "Vencido > 90 d", bad: true },
    { key: "vencido_60_90", label: "Vencido 60-90 d", bad: true },
    { key: "vencido_30_60", label: "Vencido 30-60 d", bad: true },
    { key: "vencido_0_30", label: "Vencido 0-30 d", bad: true },
    { key: "vence_0_30", label: "Vence en 0-30 d" },
    { key: "vence_30plus", label: "Vence en > 30 d" },
];

function AgingTable({
    title, subtitle, buckets, color,
}: {
    title: string; subtitle: string;
    buckets: import("@/lib/api").AnalyticsAgingBuckets;
    color: "emerald" | "red";
}) {
    const total = AGING_LABELS.reduce((s, b) => s + buckets[b.key].importe, 0);
    const empty = total === 0;
    const Icon = color === "emerald" ? TrendingUp : TrendingDown;
    return (
        <div className="bg-card border border-border rounded-2xl p-6">
            <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                <Icon className={`w-4 h-4 ${color === "emerald" ? "text-emerald-400" : "text-red-400"}`} /> {title}
            </h2>
            <p className="text-xs text-muted-foreground mb-5">{subtitle}</p>
            {empty ? (
                <div className="h-[180px] flex items-center justify-center text-sm text-muted-foreground">
                    Sin importes pendientes
                </div>
            ) : (
                <div className="space-y-3">
                    {AGING_LABELS.map(b => {
                        const v = buckets[b.key];
                        const pct = total > 0 ? (v.importe / total) * 100 : 0;
                        return (
                            <div key={String(b.key)}>
                                <div className="flex items-center justify-between text-xs mb-1">
                                    <span className={b.bad ? "text-red-400 font-medium" : "text-muted-foreground"}>{b.label}</span>
                                    <span className="text-foreground font-semibold">{v.n} · {fmt(v.importe)}€</span>
                                </div>
                                <div className="w-full h-1.5 bg-border rounded-full overflow-hidden">
                                    <div
                                        className={`h-full rounded-full transition-all duration-700 ${b.bad ? "bg-red-500/70" : "bg-emerald-500/70"}`}
                                        style={{ width: `${pct}%` }}
                                    />
                                </div>
                            </div>
                        );
                    })}
                    <div className="pt-3 mt-3 border-t border-border flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">Total pendiente</span>
                        <span className="text-foreground font-bold">{fmt(total)}€</span>
                    </div>
                </div>
            )}
        </div>
    );
}

export default function AnaliticaPage() {
    const {
        loading, error, period, setPeriod, periodLabel,
        cashflow, isDemo,
        ingresosPeriodo, gastosPeriodo, beneficioPeriodo, margenPeriodo,
        emitidasCount, recibidasCount,
        factPagadas, factPendientes, factBorrador,
        importePendienteCobro, importePendientePago, ticketMedio,
        vencenProximos, importeVencenProximos,
        topClientes, pieData,
        ventasDetalle, cobrosPagos,
        rrhh, banca,
        ia, iaDetalle,
        tasksDone, tasksFailed, tasksSuccessRate, tasksPending,
    } = useAnalitica();

    const opts = monthOptions();

    return (
        <div className="p-8 max-w-[1400px] mx-auto space-y-6">
            {/* Header */}
            <div className="flex items-start justify-between flex-wrap gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-foreground tracking-tight">Analítica</h1>
                    <p className="mt-1 text-sm text-muted-foreground">
                        Métricas financieras y operativas — {periodLabel || "cargando…"}
                        {isDemo && !loading && (
                            <span className="ml-2 text-xs text-amber-500 font-medium bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">
                                Sin datos en este periodo
                            </span>
                        )}
                    </p>
                    {error && (
                        <p className="mt-2 text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-1.5 inline-block">
                            {error}
                        </p>
                    )}
                </div>
                <div className="flex items-center gap-2">
                    <label className="text-xs text-muted-foreground font-medium">Periodo</label>
                    <select
                        value={period}
                        onChange={(e) => setPeriod(e.target.value)}
                        disabled={loading}
                        className="bg-card border border-border rounded-lg px-3 py-1.5 text-sm text-foreground hover:border-primary/40 focus:outline-none focus:border-primary transition-colors"
                    >
                        {opts.map(o => (
                            <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Aviso datos demo en banca */}
            {banca.has_demo_data && (
                <div className="flex items-start gap-3 p-4 rounded-2xl border border-amber-500/30 bg-amber-500/5">
                    <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                    <div className="flex-1 text-sm">
                        <p className="font-medium text-amber-300">Hay movimientos bancarios DEMO en tu cuenta</p>
                        <p className="text-muted-foreground text-xs mt-1">
                            Generados por el botón &quot;Sincronizar banco&quot; mientras no tengas PSD2 conectado.
                            Las métricas de banca y reconciliación los excluyen automáticamente.
                            Bórralos cuando quieras desde <code className="px-1 py-0.5 rounded bg-amber-500/10 text-amber-300">DELETE /api/v1/banking/transactions/demo</code>.
                        </p>
                    </div>
                </div>
            )}

            {/* Stacked sections */}
            <div className="space-y-12">
                {/* ── RESUMEN ───────────────────────────────────────────── */}
                <section className="space-y-8">
                    <SectionHeader icon={Activity} title="Resumen" subtitle="KPIs principales del periodo" />
                    {/* KPIs del periodo */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                        <KpiCard
                            label={`Ingresos · ${periodLabel}`}
                            value={`${fmt(ingresosPeriodo)}€`}
                            sub={`${emitidasCount} emitidas en total`}
                            icon={TrendingUp}
                            color="emerald"
                        />
                        <KpiCard
                            label={`Gastos · ${periodLabel}`}
                            value={`${fmt(gastosPeriodo)}€`}
                            sub={`${recibidasCount} recibidas en total`}
                            icon={TrendingDown}
                            color="red"
                        />
                        <KpiCard
                            label="Beneficio del periodo"
                            value={`${fmt(beneficioPeriodo)}€`}
                            sub={`Margen: ${margenPeriodo}%`}
                            icon={Activity}
                            color="indigo"
                        />
                        <KpiCard
                            label="Éxito agentes IA"
                            value={`${tasksSuccessRate}%`}
                            sub={`${tasksDone} tareas completadas`}
                            icon={BrainCircuit}
                            color="amber"
                        />
                    </div>

                    {/* Avisos de cobro */}
                    {(vencenProximos > 0 || importePendienteCobro > 0) && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {vencenProximos > 0 && (
                                <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-5 flex items-center justify-between">
                                    <div>
                                        <p className="text-xs text-amber-300 uppercase font-semibold tracking-wide">Vencen en 7 días</p>
                                        <p className="text-xl font-bold text-foreground mt-1">{vencenProximos} facturas</p>
                                        <p className="text-xs text-muted-foreground mt-1">{fmt(importeVencenProximos)}€ pendientes de cobro</p>
                                    </div>
                                    <Clock className="w-8 h-8 text-amber-400/60" />
                                </div>
                            )}
                            {importePendienteCobro > 0 && (
                                <div className="rounded-2xl border border-border bg-card p-5 flex items-center justify-between">
                                    <div>
                                        <p className="text-xs text-muted-foreground uppercase font-semibold tracking-wide">Pendiente de cobro total</p>
                                        <p className="text-xl font-bold text-foreground mt-1">{fmt(importePendienteCobro)}€</p>
                                        <p className="text-xs text-muted-foreground mt-1">{factPendientes} facturas emitidas sin cobrar</p>
                                    </div>
                                    <FileText className="w-8 h-8 text-muted-foreground/40" />
                                </div>
                            )}
                        </div>
                    )}

                    {/* Gráficos principales */}
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        <div className="lg:col-span-2 bg-card border border-border rounded-2xl p-6 shadow-lg shadow-black/20">
                            <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                                <Activity className="w-4 h-4 text-primary" /> Evolución del Cashflow
                            </h2>
                            <p className="text-xs text-muted-foreground mb-6">Ingresos vs Gastos — Últimos 6 meses</p>
                            <div className="h-[240px]">
                                {cashflow.length === 0 || cashflow.every(c => c.ingresos === 0 && c.gastos === 0) ? (
                                    <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                                        Sin datos de cashflow en los últimos 6 meses
                                    </div>
                                ) : (
                                    <ResponsiveContainer width="100%" height="100%">
                                        <AreaChart data={cashflow} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                                            <defs>
                                                <linearGradient id="colorIn2" x1="0" y1="0" x2="0" y2="1">
                                                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
                                                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                                                </linearGradient>
                                                <linearGradient id="colorOut2" x1="0" y1="0" x2="0" y2="1">
                                                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.25} />
                                                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                                                </linearGradient>
                                            </defs>
                                            <XAxis dataKey="month" stroke="#52525b" fontSize={12} tickLine={false} axisLine={false} />
                                            <YAxis stroke="#52525b" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                                            <RTooltip content={<CustomTooltip />} />
                                            <Legend wrapperStyle={{ fontSize: 12, color: "#71717a" }} />
                                            <Area type="monotone" dataKey="ingresos" name="Ingresos" stroke="#10b981" strokeWidth={2.5} fillOpacity={1} fill="url(#colorIn2)" />
                                            <Area type="monotone" dataKey="gastos" name="Gastos" stroke="#ef4444" strokeWidth={2.5} fillOpacity={1} fill="url(#colorOut2)" />
                                        </AreaChart>
                                    </ResponsiveContainer>
                                )}
                            </div>
                        </div>

                        <div className="bg-card border border-border rounded-2xl p-6 shadow-lg shadow-black/20">
                            <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                                <FileText className="w-4 h-4 text-primary" /> Estado de Facturas
                            </h2>
                            <p className="text-xs text-muted-foreground mb-4">Distribución por importe (acumulado)</p>
                            {pieData.length === 0 ? (
                                <div className="h-[180px] flex items-center justify-center text-sm text-muted-foreground">
                                    Sin facturas emitidas
                                </div>
                            ) : (
                                <>
                                    <div className="h-[180px] w-full">
                                        <ResponsiveContainer width="100%" height="100%">
                                            <PieChart>
                                                <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={80} paddingAngle={3} dataKey="value">
                                                    {pieData.map((_, i) => (
                                                        <Cell key={i} fill={COLORS_PIE[i % COLORS_PIE.length]} />
                                                    ))}
                                                </Pie>
                                                <RTooltip formatter={(v) => [`${fmt(Number(v ?? 0))}€`]} contentStyle={{ backgroundColor: "#18181b", borderColor: "#27272a", borderRadius: "8px", fontSize: "12px" }} />
                                            </PieChart>
                                        </ResponsiveContainer>
                                    </div>
                                    <div className="space-y-2 mt-2">
                                        {pieData.map((d, i) => (
                                            <div key={d.name} className="flex items-center justify-between text-xs">
                                                <div className="flex items-center gap-2">
                                                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS_PIE[i % COLORS_PIE.length] }} />
                                                    <span className="text-muted-foreground">{d.name}</span>
                                                </div>
                                                <span className="text-foreground font-medium">{fmt(d.value)}€</span>
                                            </div>
                                        ))}
                                    </div>
                                </>
                            )}
                        </div>
                    </div>

                    {/* Resumen de estados de factura */}
                    {!loading && (
                        <div className="grid grid-cols-3 gap-4">
                            {[
                                { label: "Facturas Cobradas", count: factPagadas, color: "text-emerald-400", bg: "bg-emerald-500/5 border-emerald-500/20" },
                                { label: "Facturas Pendientes", count: factPendientes, color: "text-amber-400", bg: "bg-amber-500/5 border-amber-500/20" },
                                { label: "Borradores", count: factBorrador, color: "text-muted-foreground", bg: "bg-muted border-border" },
                            ].map(item => (
                                <div key={item.label} className={`rounded-2xl border ${item.bg} p-5 flex items-center justify-between`}>
                                    <span className="text-sm text-muted-foreground">{item.label}</span>
                                    <span className={`text-2xl font-bold ${item.color}`}>{item.count}</span>
                                </div>
                            ))}
                        </div>
                    )}

                {/* ── VENTAS ────────────────────────────────────────────── */}
                </section>
                <section className="space-y-6">
                    <SectionHeader icon={TrendingUp} title="Ventas" subtitle="Facturación emitida, productos, IVA y patrones temporales" />
                    {/* KPIs ventas */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                        <KpiCard
                            label={`Ingresos · ${periodLabel}`}
                            value={`${fmt(ingresosPeriodo)}€`}
                            sub={`${emitidasCount} facturas emitidas`}
                            icon={TrendingUp}
                            color="emerald"
                        />
                        <KpiCard
                            label="Ticket medio"
                            value={`${fmt(ticketMedio)}€`}
                            sub="Por factura del periodo"
                            icon={Coins}
                            color="indigo"
                        />
                        <KpiCard
                            label="Pendiente de cobro"
                            value={`${fmt(importePendienteCobro)}€`}
                            sub={`${factPendientes} sin cobrar`}
                            icon={Clock}
                            color="amber"
                        />
                        <KpiCard
                            label="Facturas cobradas"
                            value={`${factPagadas}`}
                            sub={`${factBorrador} borradores`}
                            icon={FileText}
                            color="indigo"
                        />
                    </div>

                    {/* Top clientes + Facturación por mes */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <div className="bg-card border border-border rounded-2xl p-6">
                            <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                                <Users className="w-4 h-4 text-primary" /> Top Clientes
                            </h2>
                            <p className="text-xs text-muted-foreground mb-5">Por volumen en {periodLabel}</p>
                            {topClientes.length === 0 ? (
                                <div className="h-[160px] flex items-center justify-center text-sm text-muted-foreground">
                                    Sin clientes facturados este periodo
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    {topClientes.map((c, i) => {
                                        const maxVal = topClientes[0].total || 1;
                                        const pct = Math.round((c.total / maxVal) * 100);
                                        return (
                                            <div key={c.name}>
                                                <div className="flex items-center justify-between mb-1.5 text-xs">
                                                    <span className="text-foreground font-medium truncate max-w-[160px]">{c.name}</span>
                                                    <span className="text-foreground font-semibold ml-2 shrink-0">{fmt(c.total)}€</span>
                                                </div>
                                                <div className="w-full h-1.5 bg-border rounded-full overflow-hidden">
                                                    <div
                                                        className="h-full rounded-full transition-all duration-700"
                                                        style={{
                                                            width: `${pct}%`,
                                                            background: `linear-gradient(90deg, ${COLORS_PIE[i % COLORS_PIE.length]}, ${COLORS_PIE[(i + 1) % COLORS_PIE.length]})`
                                                        }}
                                                    />
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>

                        <div className="bg-card border border-border rounded-2xl p-6">
                            <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                                <FileText className="w-4 h-4 text-primary" /> Facturación por Mes
                            </h2>
                            <p className="text-xs text-muted-foreground mb-5">Ingresos vs Gastos</p>
                            <div className="h-[220px]">
                                {cashflow.length === 0 ? (
                                    <div className="h-full flex items-center justify-center text-sm text-muted-foreground">Sin datos mensuales</div>
                                ) : (
                                    <ResponsiveContainer width="100%" height="100%">
                                        <BarChart data={cashflow} margin={{ top: 5, right: 5, left: -25, bottom: 0 }} barGap={4}>
                                            <XAxis dataKey="month" stroke="#52525b" fontSize={11} tickLine={false} axisLine={false} />
                                            <YAxis stroke="#52525b" fontSize={10} tickLine={false} axisLine={false} tickFormatter={v => `${(v / 1000).toFixed(0)}k`} />
                                            <RTooltip content={<CustomTooltip />} />
                                            <Bar dataKey="ingresos" name="Ingresos" fill="#10b981" radius={[4, 4, 0, 0]} />
                                            <Bar dataKey="gastos" name="Gastos" fill="#ef4444" radius={[4, 4, 0, 0]} />
                                        </BarChart>
                                    </ResponsiveContainer>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Top productos + IVA */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <div className="bg-card border border-border rounded-2xl p-6">
                            <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                                <Package className="w-4 h-4 text-primary" /> Top productos
                            </h2>
                            <p className="text-xs text-muted-foreground mb-5">Por importe facturado en {periodLabel}</p>
                            {ventasDetalle.top_productos.length === 0 ? (
                                <div className="h-[140px] flex items-center justify-center text-sm text-muted-foreground">
                                    Sin líneas con producto asignado en este periodo
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    {ventasDetalle.top_productos.map((p, i) => {
                                        const maxVal = ventasDetalle.top_productos[0].total || 1;
                                        const pct = Math.round((p.total / maxVal) * 100);
                                        return (
                                            <div key={p.name}>
                                                <div className="flex items-center justify-between mb-1.5 text-xs">
                                                    <span className="text-foreground font-medium truncate max-w-[200px]">{p.name}</span>
                                                    <span className="text-foreground font-semibold ml-2 shrink-0">
                                                        {fmtInt(p.cantidad)} · {fmt(p.total)}€
                                                    </span>
                                                </div>
                                                <div className="w-full h-1.5 bg-border rounded-full overflow-hidden">
                                                    <div
                                                        className="h-full rounded-full transition-all duration-700"
                                                        style={{
                                                            width: `${pct}%`,
                                                            background: `linear-gradient(90deg, ${COLORS_PIE[i % COLORS_PIE.length]}, ${COLORS_PIE[(i + 1) % COLORS_PIE.length]})`
                                                        }}
                                                    />
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>

                        <div className="bg-card border border-border rounded-2xl p-6">
                            <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                                <Percent className="w-4 h-4 text-primary" /> Desglose por IVA
                            </h2>
                            <p className="text-xs text-muted-foreground mb-5">Base imponible e IVA repercutido por tipo</p>
                            {ventasDetalle.iva_breakdown.length === 0 ? (
                                <div className="h-[140px] flex items-center justify-center text-sm text-muted-foreground">
                                    Sin facturas con líneas en este periodo
                                </div>
                            ) : (
                                <div className="overflow-hidden rounded-xl border border-border">
                                    <table className="w-full text-xs">
                                        <thead className="bg-muted">
                                            <tr>
                                                <th className="text-left py-2 px-3 text-muted-foreground font-medium">Tipo</th>
                                                <th className="text-right py-2 px-3 text-muted-foreground font-medium">Base</th>
                                                <th className="text-right py-2 px-3 text-muted-foreground font-medium">IVA</th>
                                                <th className="text-right py-2 px-3 text-muted-foreground font-medium">Total</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {ventasDetalle.iva_breakdown.map((iv) => (
                                                <tr key={iv.rate} className="border-t border-border">
                                                    <td className="py-2 px-3 text-foreground font-medium">{iv.rate}%</td>
                                                    <td className="py-2 px-3 text-right text-foreground">{fmt(iv.base)}€</td>
                                                    <td className="py-2 px-3 text-right text-foreground">{fmt(iv.iva)}€</td>
                                                    <td className="py-2 px-3 text-right text-foreground font-semibold">{fmt(iv.total)}€</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Facturación por día de la semana */}
                    <div className="bg-card border border-border rounded-2xl p-6">
                        <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                            <CalendarDays className="w-4 h-4 text-primary" /> Facturación por día de la semana
                        </h2>
                        <p className="text-xs text-muted-foreground mb-5">Volumen de ingresos por día — {periodLabel}</p>
                        <div className="h-[220px]">
                            {ventasDetalle.por_dia_semana.every(d => d.ingresos === 0) ? (
                                <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                                    Sin facturas emitidas en este periodo
                                </div>
                            ) : (
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={ventasDetalle.por_dia_semana} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
                                        <XAxis dataKey="dia" stroke="#52525b" fontSize={11} tickLine={false} axisLine={false} />
                                        <YAxis stroke="#52525b" fontSize={10} tickLine={false} axisLine={false} tickFormatter={v => `${(v / 1000).toFixed(0)}k`} />
                                        <RTooltip content={<CustomTooltip />} />
                                        <Bar dataKey="ingresos" name="Ingresos" fill="#6366f1" radius={[4, 4, 0, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            )}
                        </div>
                    </div>

                {/* ── FINANZAS ──────────────────────────────────────────── */}
                </section>
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

                {/* ── RRHH ──────────────────────────────────────────────── */}
                </section>
                <section className="space-y-6">
                    <SectionHeader icon={Briefcase} title="RRHH" subtitle="Plantilla, nóminas, jornadas y vacaciones" />
                    {/* KPIs RRHH */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                        <KpiCard
                            label="Empleados activos"
                            value={`${fmtInt(rrhh.empleados_activos)}`}
                            sub={`${rrhh.por_departamento.length} departamentos`}
                            icon={Users}
                            color="indigo"
                        />
                        <KpiCard
                            label="Coste nóminas"
                            value={`${fmt(rrhh.coste_nominas_periodo)}€`}
                            sub={`Media: ${fmt(rrhh.coste_medio_empleado)}€/empleado`}
                            icon={Briefcase}
                            color="red"
                        />
                        <KpiCard
                            label="Horas extra"
                            value={`${fmt(rrhh.horas_extra_periodo)}h`}
                            sub={`Ordinarias: ${fmt(rrhh.horas_ordinarias_periodo)}h`}
                            icon={Timer}
                            color="amber"
                        />
                        <KpiCard
                            label="Vacaciones pendientes"
                            value={`${rrhh.vacaciones_pendientes}`}
                            sub={`${rrhh.vacaciones_aprobadas_periodo} aprobadas este periodo`}
                            icon={Plane}
                            color="emerald"
                        />
                    </div>

                    {/* Plantilla por departamento + nóminas */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <div className="bg-card border border-border rounded-2xl p-6">
                            <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                                <Building2 className="w-4 h-4 text-primary" /> Plantilla por departamento
                            </h2>
                            <p className="text-xs text-muted-foreground mb-5">Empleados activos y coste base anual</p>
                            {rrhh.por_departamento.length === 0 ? (
                                <div className="h-[140px] flex items-center justify-center text-sm text-muted-foreground">
                                    Sin empleados activos
                                </div>
                            ) : (
                                <div className="overflow-hidden rounded-xl border border-border">
                                    <table className="w-full text-xs">
                                        <thead className="bg-muted">
                                            <tr>
                                                <th className="text-left py-2 px-3 text-muted-foreground font-medium">Departamento</th>
                                                <th className="text-right py-2 px-3 text-muted-foreground font-medium">Empleados</th>
                                                <th className="text-right py-2 px-3 text-muted-foreground font-medium">Coste base</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {rrhh.por_departamento.map(d => (
                                                <tr key={d.departamento} className="border-t border-border">
                                                    <td className="py-2 px-3 text-foreground font-medium">{d.departamento}</td>
                                                    <td className="py-2 px-3 text-right text-foreground">{d.empleados}</td>
                                                    <td className="py-2 px-3 text-right text-foreground font-semibold">{fmt(d.coste_base)}€</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>

                        <div className="bg-card border border-border rounded-2xl p-6">
                            <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                                <Briefcase className="w-4 h-4 text-primary" /> Nóminas {periodLabel}
                            </h2>
                            <p className="text-xs text-muted-foreground mb-5">Estado de las nóminas del periodo</p>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
                                    <p className="text-xs text-emerald-400 uppercase tracking-wide">Pagadas</p>
                                    <p className="text-2xl font-bold text-emerald-400 mt-1">{rrhh.nominas_pagadas}</p>
                                </div>
                                <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
                                    <p className="text-xs text-amber-400 uppercase tracking-wide">Pendientes</p>
                                    <p className="text-2xl font-bold text-amber-400 mt-1">{rrhh.nominas_pendientes}</p>
                                </div>
                                <div className="rounded-xl border border-border bg-muted p-4 col-span-2">
                                    <p className="text-xs text-muted-foreground uppercase tracking-wide">Coste total nóminas</p>
                                    <p className="text-2xl font-bold text-foreground mt-1">{fmt(rrhh.coste_nominas_periodo)}€</p>
                                    <p className="text-xs text-muted-foreground mt-1">
                                        Media por empleado: <span className="text-foreground font-medium">{fmt(rrhh.coste_medio_empleado)}€</span>
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Horas + Gastos */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <div className="bg-card border border-border rounded-2xl p-6">
                            <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                                <Timer className="w-4 h-4 text-primary" /> Horas trabajadas
                            </h2>
                            <p className="text-xs text-muted-foreground mb-5">Jornadas registradas en {periodLabel}</p>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <p className="text-xs text-muted-foreground uppercase tracking-wide">Ordinarias</p>
                                    <p className="text-2xl font-bold text-foreground mt-1">{fmt(rrhh.horas_ordinarias_periodo)}h</p>
                                </div>
                                <div>
                                    <p className="text-xs text-amber-400 uppercase tracking-wide">Extra</p>
                                    <p className="text-2xl font-bold text-amber-400 mt-1">{fmt(rrhh.horas_extra_periodo)}h</p>
                                </div>
                            </div>
                            {rrhh.horas_ordinarias_periodo > 0 && (
                                <div className="mt-4 pt-4 border-t border-border text-xs text-muted-foreground">
                                    Ratio horas extra:{" "}
                                    <span className="text-foreground font-medium">
                                        {((rrhh.horas_extra_periodo / (rrhh.horas_ordinarias_periodo + rrhh.horas_extra_periodo)) * 100).toFixed(1)}%
                                    </span>
                                </div>
                            )}
                        </div>

                        <div className="bg-card border border-border rounded-2xl p-6">
                            <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                                <Coins className="w-4 h-4 text-primary" /> Gastos pendientes
                            </h2>
                            <p className="text-xs text-muted-foreground mb-5">Gastos de empleados sin aprobar</p>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <p className="text-xs text-muted-foreground uppercase tracking-wide">Tickets</p>
                                    <p className="text-2xl font-bold text-foreground mt-1">{rrhh.gastos_pendientes_count}</p>
                                </div>
                                <div>
                                    <p className="text-xs text-red-400 uppercase tracking-wide">Importe</p>
                                    <p className="text-2xl font-bold text-red-400 mt-1">{fmt(rrhh.gastos_pendientes_importe)}€</p>
                                </div>
                            </div>
                        </div>
                    </div>

                {/* ── IA ────────────────────────────────────────────────── */}
                </section>
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
            </div>
        </div>
    );
}
