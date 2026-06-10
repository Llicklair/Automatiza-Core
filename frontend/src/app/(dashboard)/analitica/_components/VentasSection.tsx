"use client";

import {
    TrendingUp, FileText, Users, Clock,
    Package, Percent, CalendarDays, Coins,
} from "lucide-react";
import {
    BarChart, Bar, XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer
} from "recharts";
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
    return (
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
        </section>
    );
}
