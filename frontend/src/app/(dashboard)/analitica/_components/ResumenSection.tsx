"use client";

import {
    TrendingUp, TrendingDown, FileText, Activity, BrainCircuit, Clock,
    Package, PackageMinus, AlertTriangle,
} from "lucide-react";
import {
    AreaChart, Area, PieChart, Pie, Cell,
    XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer, Legend
} from "recharts";
import { useTranslations } from "next-intl";
import type { AnalyticsDashboard } from "@/lib/api";
import { KpiCard } from "./KpiCard";
import { SectionHeader } from "./SectionHeader";
import { CustomTooltip } from "./CustomTooltip";
import { fmt, COLORS_PIE } from "./utils";

interface ResumenSectionProps {
    loading: boolean;
    periodLabel: string;
    cashflow: AnalyticsDashboard["cashflow"];
    pieData: AnalyticsDashboard["estado_facturas"];
    ingresosPeriodo: number;
    gastosPeriodo: number;
    beneficioPeriodo: number;
    margenPeriodo: number;
    emitidasCount: number;
    recibidasCount: number;
    factPagadas: number;
    factPendientes: number;
    factBorrador: number;
    importePendienteCobro: number;
    vencenProximos: number;
    importeVencenProximos: number;
    tasksDone: number;
    tasksSuccessRate: number;
    productosActivos: number;
    unidadesStock: number;
    valorStockEur: number;
    bajasUnits: number;
    bajasValueEur: number;
    belowMinCount: number;
}

export function ResumenSection({
    loading, periodLabel, cashflow, pieData,
    ingresosPeriodo, gastosPeriodo, beneficioPeriodo, margenPeriodo,
    emitidasCount, recibidasCount,
    factPagadas, factPendientes, factBorrador,
    importePendienteCobro, vencenProximos, importeVencenProximos,
    tasksDone, tasksSuccessRate,
    productosActivos, unidadesStock, valorStockEur,
    bajasUnits, bajasValueEur, belowMinCount,
}: ResumenSectionProps) {
    const t = useTranslations("analitica");
    return (
        <section className="space-y-8">
            <SectionHeader icon={Activity} title={t("resumen.title")} subtitle={t("resumen.subtitle")} />
            {/* KPIs del periodo */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                <KpiCard
                    label={t("resumen.kpiIngresos", { period: periodLabel })}
                    value={`${fmt(ingresosPeriodo)}€`}
                    sub={t("resumen.kpiIngresosSub", { count: emitidasCount })}
                    icon={TrendingUp}
                    color="emerald"
                />
                <KpiCard
                    label={t("resumen.kpiGastos", { period: periodLabel })}
                    value={`${fmt(gastosPeriodo)}€`}
                    sub={t("resumen.kpiGastosSub", { count: recibidasCount })}
                    icon={TrendingDown}
                    color="red"
                />
                <KpiCard
                    label={t("resumen.kpiBeneficio")}
                    value={`${fmt(beneficioPeriodo)}€`}
                    sub={t("resumen.kpiBeneficioSub", { margin: margenPeriodo })}
                    icon={Activity}
                    color="indigo"
                />
                <KpiCard
                    label={t("resumen.kpiIaExito")}
                    value={`${tasksSuccessRate}%`}
                    sub={t("resumen.kpiIaExitoSub", { count: tasksDone })}
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
                                <p className="text-xs text-amber-300 uppercase font-semibold tracking-wide">{t("resumen.dueSoonTitle")}</p>
                                <p className="text-xl font-bold text-foreground mt-1">{t("resumen.dueSoonCount", { count: vencenProximos })}</p>
                                <p className="text-xs text-muted-foreground mt-1">{t("resumen.dueSoonAmount", { amount: fmt(importeVencenProximos) })}</p>
                            </div>
                            <Clock className="w-8 h-8 text-amber-400/60" />
                        </div>
                    )}
                    {importePendienteCobro > 0 && (
                        <div className="rounded-2xl border border-border bg-card p-5 flex items-center justify-between">
                            <div>
                                <p className="text-xs text-muted-foreground uppercase font-semibold tracking-wide">{t("resumen.pendingTotalTitle")}</p>
                                <p className="text-xl font-bold text-foreground mt-1">{fmt(importePendienteCobro)}€</p>
                                <p className="text-xs text-muted-foreground mt-1">{t("resumen.pendingTotalSub", { count: factPendientes })}</p>
                            </div>
                            <FileText className="w-8 h-8 text-muted-foreground/40" />
                        </div>
                    )}
                </div>
            )}

            {/* Inventario: estado de stock + mermas y bajo mínimo */}
            {(productosActivos > 0 || bajasUnits > 0 || belowMinCount > 0) && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {productosActivos > 0 && (
                        <div className="rounded-2xl border border-border bg-card p-5 flex items-center justify-between">
                            <div>
                                <p className="text-xs text-muted-foreground uppercase font-semibold tracking-wide">{t("resumen.stockValueTitle")}</p>
                                <p className="text-xl font-bold text-foreground mt-1">{fmt(valorStockEur)}€</p>
                                <p className="text-xs text-muted-foreground mt-1">{t("resumen.stockValueSub", { units: unidadesStock, products: productosActivos })}</p>
                            </div>
                            <Package className="w-8 h-8 text-muted-foreground/40" />
                        </div>
                    )}
                    {bajasUnits > 0 && (
                    <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-5 flex items-center justify-between">
                        <div>
                            <p className="text-xs text-rose-300 uppercase font-semibold tracking-wide">{t("resumen.mermasTitle")}</p>
                            <p className="text-xl font-bold text-foreground mt-1">{t("resumen.mermasCount", { count: bajasUnits })}</p>
                            <p className="text-xs text-muted-foreground mt-1">{t("resumen.mermasAmount", { amount: fmt(bajasValueEur) })}</p>
                        </div>
                        <PackageMinus className="w-8 h-8 text-rose-400/60" />
                    </div>
                    )}
                    {belowMinCount > 0 && (
                        <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-5 flex items-center justify-between">
                            <div>
                                <p className="text-xs text-amber-300 uppercase font-semibold tracking-wide">{t("resumen.belowMinTitle")}</p>
                                <p className="text-xl font-bold text-foreground mt-1">{t("resumen.belowMinCount", { count: belowMinCount })}</p>
                            </div>
                            <AlertTriangle className="w-8 h-8 text-amber-400/60" />
                        </div>
                    )}
                </div>
            )}

            {/* Gráficos principales */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 bg-card border border-border rounded-2xl p-6 shadow-lg shadow-black/20">
                    <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                        <Activity className="w-4 h-4 text-primary" /> {t("resumen.cashflowTitle")}
                    </h2>
                    <p className="text-xs text-muted-foreground mb-6">{t("resumen.cashflowSubtitle")}</p>
                    <div className="h-[240px]">
                        {cashflow.length === 0 || cashflow.every(c => c.ingresos === 0 && c.gastos === 0) ? (
                            <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                                {t("resumen.cashflowEmpty")}
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
                                    <Area type="monotone" dataKey="ingresos" name={t("series.ingresos")} stroke="#10b981" strokeWidth={2.5} fillOpacity={1} fill="url(#colorIn2)" />
                                    <Area type="monotone" dataKey="gastos" name={t("series.gastos")} stroke="#ef4444" strokeWidth={2.5} fillOpacity={1} fill="url(#colorOut2)" />
                                </AreaChart>
                            </ResponsiveContainer>
                        )}
                    </div>
                </div>

                <div className="bg-card border border-border rounded-2xl p-6 shadow-lg shadow-black/20">
                    <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                        <FileText className="w-4 h-4 text-primary" /> {t("resumen.invoiceStatusTitle")}
                    </h2>
                    <p className="text-xs text-muted-foreground mb-4">{t("resumen.invoiceStatusSubtitle")}</p>
                    {pieData.length === 0 ? (
                        <div className="h-[180px] flex items-center justify-center text-sm text-muted-foreground">
                            {t("resumen.invoiceStatusEmpty")}
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
                        { key: "cobradas", label: t("resumen.statusPaid"), count: factPagadas, color: "text-emerald-400", bg: "bg-emerald-500/5 border-emerald-500/20" },
                        { key: "pendientes", label: t("resumen.statusPending"), count: factPendientes, color: "text-amber-400", bg: "bg-amber-500/5 border-amber-500/20" },
                        { key: "borradores", label: t("resumen.statusDraft"), count: factBorrador, color: "text-muted-foreground", bg: "bg-muted border-border" },
                    ].map(item => (
                        <div key={item.key} className={`rounded-2xl border ${item.bg} p-5 flex items-center justify-between`}>
                            <span className="text-sm text-muted-foreground">{item.label}</span>
                            <span className={`text-2xl font-bold ${item.color}`}>{item.count}</span>
                        </div>
                    ))}
                </div>
            )}
        </section>
    );
}
