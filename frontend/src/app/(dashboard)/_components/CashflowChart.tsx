"use client";

import { Activity } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer } from "recharts";
import { useTranslations } from "next-intl";

interface CashflowChartProps {
    cashflow: any[];
}

export function CashflowChart({ cashflow }: CashflowChartProps) {
    const t = useTranslations("dashboard");
    if (cashflow.length === 0) return null;

    return (
        <div className="bg-card border border-border rounded-2xl p-6 shadow-lg shadow-black/20">
            <h2 className="text-sm font-semibold text-foreground mb-6 flex items-center gap-2">
                <Activity className="w-4 h-4 text-muted-foreground" /> {t("cashflow.title")}
            </h2>
            <div className="h-[250px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={cashflow} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <defs>
                            <linearGradient id="colorIn" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id="colorOut" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <XAxis dataKey="month" stroke="#52525b" fontSize={12} tickLine={false} axisLine={false} />
                        <YAxis stroke="#52525b" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`} />
                        <RTooltip
                            contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '8px', fontSize: '12px' }}
                            itemStyle={{ color: '#e4e4e7' }}
                            formatter={((value: unknown) => [`${Number(value)?.toLocaleString() ?? 0}€`]) as never}
                        />
                        <Area type="monotone" dataKey="ingresos" name={t("cashflow.income")} stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#colorIn)" />
                        <Area type="monotone" dataKey="gastos" name={t("cashflow.expenses")} stroke="#ef4444" strokeWidth={2} fillOpacity={1} fill="url(#colorOut)" />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
