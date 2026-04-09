"use client";

import { useEffect, useState } from "react";
import { api, type Invoice, type Task } from "@/lib/api";
import {
    TrendingUp, TrendingDown, FileText, Users, Zap,
    ArrowUp, ArrowDown, BrainCircuit, Clock, CheckCircle2,
    XCircle, Activity
} from "lucide-react";
import {
    AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
    XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer, Legend
} from "recharts";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmt(n: number) {
    return n.toLocaleString("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function KpiCard({
    label, value, sub, icon: Icon, trend, color = "indigo"
}: {
    label: string; value: string; sub?: string; icon: any;
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

// ─── Tooltip personalizado ────────────────────────────────────────────────────

const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload?.length) {
        return (
            <div className="bg-card border border-border rounded-xl p-3 text-xs shadow-xl">
                <p className="text-muted-foreground mb-2 font-medium">{label}</p>
                {payload.map((p: any) => (
                    <p key={p.name} style={{ color: p.color }} className="font-semibold">
                        {p.name}: {fmt(p.value)}€
                    </p>
                ))}
            </div>
        );
    }
    return null;
};

const COLORS_PIE = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"];

// ─── Componente principal ─────────────────────────────────────────────────────

export default function AnaliticaPage() {
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [tasks, setTasks] = useState<Task[]>([]);
    const [cashflow, setCashflow] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        Promise.all([
            api.erp.invoices.list({ limit: 200 }).catch(() => []),
            api.tasks.list({ limit: 100 }).catch(() => []),
            api.banking.analytics().catch(() => ({ cashflow: [], insights: [] })),
        ]).then(([inv, tsk, analytics]) => {
            setInvoices(inv);
            setTasks(tsk);
            setCashflow((analytics as any).cashflow || []);
        }).finally(() => setLoading(false));
    }, []);

    // ── Calcular KPIs ─────────────────────────────────────────────────────────
    const emitidas = invoices.filter(i => i.invoice_type === "issued");
    const recibidas = invoices.filter(i => i.invoice_type === "received");

    const totalIngresos = emitidas.reduce((s, i) => s + Number(i.amount_total), 0);
    const totalGastos = recibidas.reduce((s, i) => s + Number(i.amount_total), 0);
    const beneficio = totalIngresos - totalGastos;
    const margen = totalIngresos > 0 ? Math.round((beneficio / totalIngresos) * 100) : 0;

    const factPagadas = emitidas.filter(i => i.status === "paid").length;
    const factPendientes = emitidas.filter(i => i.status === "pending").length;
    const factBorrador = emitidas.filter(i => i.status === "draft").length;

    // Top clientes por facturación
    const clientMap: Record<string, number> = {};
    emitidas.forEach(inv => {
        const name = inv.client?.name || "Desconocido";
        clientMap[name] = (clientMap[name] || 0) + Number(inv.amount_total);
    });
    const topClientes = Object.entries(clientMap)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5)
        .map(([name, total]) => ({ name, total }));

    // Distribución por estado
    const pieData = [
        { name: "Cobradas", value: emitidas.filter(i => i.status === "paid").reduce((s, i) => s + Number(i.amount_total), 0) },
        { name: "Pendientes", value: emitidas.filter(i => i.status === "pending").reduce((s, i) => s + Number(i.amount_total), 0) },
        { name: "Borradores", value: emitidas.filter(i => i.status === "draft").reduce((s, i) => s + Number(i.amount_total), 0) },
    ].filter(d => d.value > 0);

    // Métricas de IA
    const tasksDone = tasks.filter(t => t.status === "done").length;
    const tasksFailed = tasks.filter(t => t.status === "failed").length;
    const tasksTotal = tasks.length;
    const tasksSuccessRate = tasksTotal > 0 ? Math.round((tasksDone / tasksTotal) * 100) : 0;

    const isDemo = invoices.length === 0;

    return (
        <div className="p-8 max-w-[1400px] mx-auto space-y-8">
            {/* Header */}
            <div className="flex items-start justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-foreground tracking-tight">Analítica</h1>
                    <p className="mt-1 text-sm text-muted-foreground">
                        Métricas financieras y operativas en tiempo real
                        {isDemo && <span className="ml-2 text-xs text-amber-500 font-medium bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">Sin datos — registra facturas para ver métricas reales</span>}
                    </p>
                </div>
                <div className="text-xs text-muted-foreground/60 font-mono bg-card border border-border px-3 py-1.5 rounded-lg">
                    {new Date().toLocaleDateString("es-ES", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}
                </div>
            </div>

            {/* KPIs Row */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                <KpiCard
                    label="Ingresos totales"
                    value={`${fmt(totalIngresos)}€`}
                    sub={`${emitidas.length} facturas emitidas`}
                    icon={TrendingUp}
                    color="emerald"
                />
                <KpiCard
                    label="Gastos totales"
                    value={`${fmt(totalGastos)}€`}
                    sub={`${recibidas.length} facturas recibidas`}
                    icon={TrendingDown}
                    color="red"
                />
                <KpiCard
                    label="Beneficio neto"
                    value={`${fmt(beneficio)}€`}
                    sub={`Margen: ${margen}%`}
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

            {/* Gráficos principales */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Cashflow evolution */}
                <div className="lg:col-span-2 bg-card border border-border rounded-2xl p-6 shadow-lg shadow-black/20">
                    <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                        <Activity className="w-4 h-4 text-primary" /> Evolución del Cashflow
                    </h2>
                    <p className="text-xs text-muted-foreground mb-6">Ingresos vs Gastos — Últimos 6 meses</p>
                    <div className="h-[240px]">
                        {cashflow.length === 0 ? (
                            <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                                {isDemo ? "Conecta tu banco o registra facturas para ver el cashflow" : "Sin datos de cashflow"}
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

                {/* Distribución por estado */}
                <div className="bg-card border border-border rounded-2xl p-6 shadow-lg shadow-black/20">
                    <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                        <FileText className="w-4 h-4 text-primary" /> Estado de Facturas
                    </h2>
                    <p className="text-xs text-muted-foreground mb-4">Distribución por importe</p>
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
                                    {pieData.map((_: any, i: number) => (
                                        <Cell key={i} fill={COLORS_PIE[i % COLORS_PIE.length]} />
                                    ))}
                                </Pie>
                                <RTooltip formatter={(v: any) => [`${fmt(Number(v))}€`]} contentStyle={{ backgroundColor: "#18181b", borderColor: "#27272a", borderRadius: "8px", fontSize: "12px" }} />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                    <div className="space-y-2 mt-2">
                        {pieData.map((d, i) => (
                            <div key={d.name} className="flex items-center justify-between text-xs">
                                <div className="flex items-center gap-2">
                                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS_PIE[i] }} />
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

            {/* Panel inferior */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                {/* Top Clientes */}
                <div className="bg-card border border-border rounded-2xl p-6">
                    <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                        <Users className="w-4 h-4 text-primary" /> Top Clientes
                    </h2>
                    <p className="text-xs text-muted-foreground mb-5">Por volumen de facturación</p>
                    {topClientes.length === 0 ? (
                        <div className="h-[160px] flex items-center justify-center text-sm text-muted-foreground">
                            Sin clientes facturados
                        </div>
                    ) : (
                    <div className="space-y-4">
                        {topClientes.map((c, i) => {
                            const maxVal = topClientes[0].total;
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

                {/* Facturación mensual por tipo */}
                <div className="bg-card border border-border rounded-2xl p-6">
                    <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                        <FileText className="w-4 h-4 text-primary" /> Facturación por Mes
                    </h2>
                    <p className="text-xs text-muted-foreground mb-5">Emitidas vs Recibidas</p>
                    <div className="h-[200px]">
                        {cashflow.length === 0 ? (
                            <div className="h-full flex items-center justify-center text-sm text-muted-foreground">Sin datos mensuales</div>
                        ) : (
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={cashflow} margin={{ top: 5, right: 5, left: -25, bottom: 0 }} barGap={4}>
                                <XAxis dataKey="month" stroke="#52525b" fontSize={11} tickLine={false} axisLine={false} />
                                <YAxis stroke="#52525b" fontSize={10} tickLine={false} axisLine={false} tickFormatter={v => `${(v / 1000).toFixed(0)}k`} />
                                <RTooltip content={<CustomTooltip />} />
                                <Bar dataKey="ingresos" name="Emitidas" fill="#6366f1" radius={[4, 4, 0, 0]} />
                                <Bar dataKey="gastos" name="Recibidas" fill="#ef4444" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                        )}
                    </div>
                </div>

                {/* Métricas de IA */}
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
                                <Clock className="w-4 h-4 text-amber-400" /> Pendientes
                            </div>
                            <span className="text-amber-400 font-bold text-sm">
                                {tasks.filter(t => t.status === "pending" || t.status === "executing").length}
                            </span>
                        </div>
                        <div className="flex items-center justify-between py-3 border-b border-border">
                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                <Zap className="w-4 h-4 text-primary" /> Tasa de éxito
                            </div>
                            <span className="text-primary font-bold text-sm">{tasksSuccessRate}%</span>
                        </div>

                        {/* Barra de progreso */}
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
