"use client";

import {
    TrendingUp, FileText, Users, Clock,
    Package, Percent, CalendarDays, Coins,
} from "lucide-react";
import {
    BarChart, Bar, XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer
} from "recharts";
import { useTranslations } from "next-intl";
import type { AnalyticsDashboard } from "@/lib/api";
import { KpiCard } from "./KpiCard";
import { SectionHeader } from "./SectionHeader";
import { CustomTooltip } from "./CustomTooltip";
import { fmt, fmtInt, COLORS_PIE } from "./utils";

interface VentasSectionProps {
    periodLabel: string;
    cashflow: AnalyticsDashboard["cashflow"];
    topClientes: AnalyticsDashboard["top_clientes"];
    ventasDetalle: AnalyticsDashboard["ventas_detalle"];
    ingresosPeriodo: number;
    emitidasCount: number;
    ticketMedio: number;
    importePendienteCobro: number;
    factPagadas: number;
    factPendientes: number;
    factBorrador: number;
}

export function VentasSection({
    periodLabel, cashflow, topClientes, ventasDetalle,
    ingresosPeriodo, emitidasCount, ticketMedio,
    importePendienteCobro, factPagadas, factPendientes, factBorrador,
}: VentasSectionProps) {
    const t = useTranslations("analitica");
    return (
        <section className="space-y-6">
            <SectionHeader icon={TrendingUp} title={t("ventas.title")} subtitle={t("ventas.subtitle")} />
            {/* KPIs ventas */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                <KpiCard
                    label={t("ventas.kpiIngresos", { period: periodLabel })}
                    value={`${fmt(ingresosPeriodo)}€`}
                    sub={t("ventas.kpiIngresosSub", { count: emitidasCount })}
                    icon={TrendingUp}
                    color="emerald"
                />
                <KpiCard
                    label={t("ventas.kpiTicketMedio")}
                    value={`${fmt(ticketMedio)}€`}
                    sub={t("ventas.kpiTicketMedioSub")}
                    icon={Coins}
                    color="indigo"
                />
                <KpiCard
                    label={t("ventas.kpiPendiente")}
                    value={`${fmt(importePendienteCobro)}€`}
                    sub={t("ventas.kpiPendienteSub", { count: factPendientes })}
                    icon={Clock}
                    color="amber"
                />
                <KpiCard
                    label={t("ventas.kpiCobradas")}
                    value={`${factPagadas}`}
                    sub={t("ventas.kpiCobradasSub", { count: factBorrador })}
                    icon={FileText}
                    color="indigo"
                />
            </div>

            {/* Top clientes + Facturación por mes */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-card border border-border rounded-2xl p-6">
                    <h2 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                        <Users className="w-4 h-4 text-primary" /> {t("ventas.topClientesTitle")}
                    </h2>
                    <p className="text-xs text-muted-foreground mb-5">{t("ventas.topClientesSubtitle", { period: periodLabel })}</p>
                    {topClientes.length === 0 ? (
                        <div className="h-[160px] flex items-center justify-center text-sm text-muted-foreground">
                            {t("ventas.topClientesEmpty")}
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
                        <FileText className="w-4 h-4 text-primary" /> {t("ventas.facturacionMesTitle")}
                    </h2>
                    <p className="text-xs text-muted-foreground mb-5">{t("ventas.facturacionMesSubtitle")}</p>
                    <div className="h-[220px]">
                        {cashflow.length === 0 ? (
                            <div className="h-full flex items-center justify-center text-sm text-muted-foreground">{t("ventas.facturacionMesEmpty")}</div>
                        ) : (
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={cashflow} margin={{ top: 5, right: 5, left: -25, bottom: 0 }} barGap={4}>
                                    <XAxis dataKey="month" stroke="#52525b" fontSize={11} tickLine={false} axisLine={false} />
                                    <YAxis stroke="#52525b" fontSize={10} tickLine={false} axisLine={false} tickFormatter={v => `${(v / 1000).toFixed(0)}k`} />
                                    <RTooltip content={<CustomTooltip />} />
                                    <Bar dataKey="ingresos" name={t("series.ingresos")} fill="#10b981" radius={[4, 4, 0, 0]} />
                                    <Bar dataKey="gastos" name={t("series.gastos")} fill="#ef4444" radius={[4, 4, 0, 0]} />
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
                        <Package className="w-4 h-4 text-primary" /> {t("ventas.topProductosTitle")}
                    </h2>
                    <p className="text-xs text-muted-foreground mb-5">{t("ventas.topProductosSubtitle", { period: periodLabel })}</p>
                    {ventasDetalle.top_productos.length === 0 ? (
                        <div className="h-[140px] flex items-center justify-center text-sm text-muted-foreground">
                            {t("ventas.topProductosEmpty")}
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
                        <Percent className="w-4 h-4 text-primary" /> {t("ventas.ivaTitle")}
                    </h2>
                    <p className="text-xs text-muted-foreground mb-5">{t("ventas.ivaSubtitle")}</p>
                    {ventasDetalle.iva_breakdown.length === 0 ? (
                        <div className="h-[140px] flex items-center justify-center text-sm text-muted-foreground">
                            {t("ventas.ivaEmpty")}
                        </div>
                    ) : (
                        <div className="overflow-hidden rounded-xl border border-border">
                            <table className="w-full text-xs">
                                <thead className="bg-muted">
                                    <tr>
                                        <th className="text-left py-2 px-3 text-muted-foreground font-medium">{t("ventas.ivaColType")}</th>
                                        <th className="text-right py-2 px-3 text-muted-foreground font-medium">{t("ventas.ivaColBase")}</th>
                                        <th className="text-right py-2 px-3 text-muted-foreground font-medium">{t("ventas.ivaColIva")}</th>
                                        <th className="text-right py-2 px-3 text-muted-foreground font-medium">{t("ventas.ivaColTotal")}</th>
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
                    <CalendarDays className="w-4 h-4 text-primary" /> {t("ventas.porDiaTitle")}
                </h2>
                <p className="text-xs text-muted-foreground mb-5">{t("ventas.porDiaSubtitle", { period: periodLabel })}</p>
                <div className="h-[220px]">
                    {ventasDetalle.por_dia_semana.every(d => d.ingresos === 0) ? (
                        <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                            {t("ventas.porDiaEmpty")}
                        </div>
                    ) : (
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={ventasDetalle.por_dia_semana} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
                                <XAxis dataKey="dia" stroke="#52525b" fontSize={11} tickLine={false} axisLine={false} />
                                <YAxis stroke="#52525b" fontSize={10} tickLine={false} axisLine={false} tickFormatter={v => `${(v / 1000).toFixed(0)}k`} />
                                <RTooltip content={<CustomTooltip />} />
                                <Bar dataKey="ingresos" name={t("series.ingresos")} fill="#6366f1" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    )}
                </div>
            </div>
        </section>
    );
}
