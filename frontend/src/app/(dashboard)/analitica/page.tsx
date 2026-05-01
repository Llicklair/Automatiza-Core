"use client";

import {
    TrendingUp, TrendingDown, FileText, Users, Zap,
    ArrowUp, ArrowDown, BrainCircuit, Clock, CheckCircle2,
    XCircle, Activity, AlertTriangle, Wallet, Briefcase,
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

// Genera las últimas 12 opciones de mes (YYYY-MM) para el selector
function monthOptions(): { value: string; label: string }[] {
    const months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
    const opts: { value: string; label: string }[] = [];
    const now = new Date();
    let y = now.getFullYear();
    let m = now.getMonth(); // 0-indexed
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

export default function AnaliticaPage() {
    const {
        loading, error, period, setPeriod, periodLabel,
        cashflow, isDemo,
        ingresosPeriodo, gastosPeriodo, beneficioPeriodo, margenPeriodo,
        emitidasCount, recibidasCount,
        factPagadas, factPendientes, factBorrador,
        importePendienteCobro, vencenProximos, importeVencenProximos,
        topClientes, pieData,
        rrhh, banca,
        tasksDone, tasksFailed, tasksSuccessRate, tasksPending,
    } = useAnalitica();

    const opts = monthOptions();

    return (
        <div className="p-8 max-w-[1400px] mx-auto space-y-8">
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

            {/* Bloques Banca y RRHH */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-card border border-border rounded-2xl p-6">
                    <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                        <Wallet className="w-4 h-4 text-primary" /> Banca
                    </h2>
                    <p className="text-xs text-muted-foreground mb-5">
                        Movimientos reales de {periodLabel} (excluye demo)
                    </p>
                    <div className="grid grid-cols-2 gap-4">
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
                            <p className="text-lg font-semibold text-emerald-400 mt-1">+{fmt(banca.entradas_periodo)}€</p>
                        </div>
                        <div>
                            <p className="text-xs text-red-400 uppercase tracking-wide">Salidas</p>
                            <p className="text-lg font-semibold text-red-400 mt-1">−{fmt(banca.salidas_periodo)}€</p>
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

                <div className="bg-card border border-border rounded-2xl p-6">
                    <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                        <Briefcase className="w-4 h-4 text-primary" /> Recursos Humanos
                    </h2>
                    <p className="text-xs text-muted-foreground mb-5">
                        Plantilla y nóminas de {periodLabel}
                    </p>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <p className="text-xs text-muted-foreground uppercase tracking-wide">Empleados activos</p>
                            <p className="text-2xl font-bold text-foreground mt-1">{fmtInt(rrhh.empleados_activos)}</p>
                        </div>
                        <div>
                            <p className="text-xs text-muted-foreground uppercase tracking-wide">Coste nóminas</p>
                            <p className="text-2xl font-bold text-foreground mt-1">{fmt(rrhh.coste_nominas_periodo)}€</p>
                        </div>
                        <div>
                            <p className="text-xs text-emerald-400 uppercase tracking-wide">Pagadas</p>
                            <p className="text-lg font-semibold text-emerald-400 mt-1">{rrhh.nominas_pagadas}</p>
                        </div>
                        <div>
                            <p className="text-xs text-amber-400 uppercase tracking-wide">Pendientes</p>
                            <p className="text-lg font-semibold text-amber-400 mt-1">{rrhh.nominas_pendientes}</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Panel inferior: top clientes + facturación + IA */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
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
                    <div className="h-[200px]">
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

                <div className="bg-card border border-border rounded-2xl p-6">
                    <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                        <BrainCircuit className="w-4 h-4 text-primary" /> Rendimiento IA
                    </h2>
                    <p className="text-xs text-muted-foreground mb-5">Estadísticas de agentes</p>

                    <div className="space-y-4">
                        <div className="flex items-center justify-between py-3 border-b border-border">
                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                <CheckCircle2 className="w-4 h-4 text-emerald-400" /> Completadas
                            </div>
                            <span className="text-emerald-400 font-bold text-sm">{tasksDone}</span>
                        </div>
                        <div className="flex items-center justify-between py-3 border-b border-border">
                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                <XCircle className="w-4 h-4 text-red-400" /> Fallidas
                            </div>
                            <span className="text-red-400 font-bold text-sm">{tasksFailed}</span>
                        </div>
                        <div className="flex items-center justify-between py-3 border-b border-border">
                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                <Clock className="w-4 h-4 text-amber-400" /> En curso
                            </div>
                            <span className="text-amber-400 font-bold text-sm">{tasksPending}</span>
                        </div>
                        <div className="flex items-center justify-between py-3 border-b border-border">
                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                <Zap className="w-4 h-4 text-primary" /> Tasa de éxito
                            </div>
                            <span className="text-primary font-bold text-sm">{tasksSuccessRate}%</span>
                        </div>

                        <div className="pt-2">
                            <div className="flex justify-between text-xs text-muted-foreground mb-2">
                                <span>Fiabilidad global</span>
                                <span className="text-foreground font-medium">{tasksSuccessRate}%</span>
                            </div>
                            <div className="w-full h-2 bg-border rounded-full overflow-hidden">
                                <div
                                    className="h-full rounded-full bg-gradient-to-r from-indigo-600 to-indigo-400 transition-all duration-1000"
                                    style={{ width: `${tasksSuccessRate}%` }}
                                />
                            </div>
                        </div>
                    </div>
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
        </div>
    );
}
