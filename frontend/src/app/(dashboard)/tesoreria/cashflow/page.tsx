"use client";

import { AreaChart, Wallet, ArrowUpRight, ArrowDownRight, CalendarDays } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { useCashflow } from "./_hooks/useCashflow";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { PageContainer } from "@/components/shared/PageContainer";

export default function CashflowPage() {
    const t = useTranslations("tesoreria");
    const { loading, filter, setFilter, totalIn, totalOut, netFlow, visibleEvents } = useCashflow();

    return (
        <PageContainer className="animate-in fade-in duration-500">
            <PageHeader
                title={t("cashflow.pageTitle")}
                description={t("cashflow.pageDescription")}
                icon={AreaChart}
            />

            {/* Cajas de resumen */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-card border border-border rounded-2xl p-6 relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                        <ArrowUpRight className="w-24 h-24 text-emerald-500" />
                    </div>
                    <div className="relative z-10">
                        <p className="text-sm font-medium text-muted-foreground mb-1">{t("cashflow.expectedInflows")}</p>
                        <p className="text-3xl font-bold text-emerald-400">
                            {totalIn.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}
                        </p>
                    </div>
                </div>

                <div className="bg-card border border-border rounded-2xl p-6 relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                        <ArrowDownRight className="w-24 h-24 text-rose-500" />
                    </div>
                    <div className="relative z-10">
                        <p className="text-sm font-medium text-muted-foreground mb-1">{t("cashflow.expectedOutflows")}</p>
                        <p className="text-3xl font-bold text-rose-400">
                            {totalOut.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}
                        </p>
                    </div>
                </div>

                <div className={cn("border rounded-2xl p-6 relative overflow-hidden", netFlow >= 0 ? "bg-emerald-500/10 border-emerald-500/20" : "bg-rose-500/10 border-rose-500/20")}>
                    <div className="absolute top-0 right-0 p-4 opacity-20">
                        <Wallet className={cn("w-24 h-24", netFlow >= 0 ? "text-emerald-500" : "text-rose-500")} />
                    </div>
                    <div className="relative z-10">
                        <p className={cn("text-sm font-medium mb-1", netFlow >= 0 ? "text-emerald-400/80" : "text-rose-400/80")}>{t("cashflow.netCashFlow")}</p>
                        <p className={cn("text-3xl font-bold", netFlow >= 0 ? "text-emerald-400" : "text-rose-400")}>
                            {netFlow.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}
                        </p>
                    </div>
                </div>
            </div>

            {/* Línea de tiempo */}
            <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-2xl flex flex-col">
                <div className="p-4 border-b border-border flex items-center justify-between bg-card">
                    <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
                        <AreaChart className="w-5 h-5 text-primary" />
                        {t("cashflow.movementsHistory")}
                    </h3>

                    <div className="flex bg-muted rounded-lg p-1 border border-border gap-0.5">
                        <Button variant="ghost" size="sm" onClick={() => setFilter('all')} className={cn("h-7 px-3 text-xs", filter === 'all' ? "bg-card text-foreground shadow-sm hover:bg-card" : "text-muted-foreground")}>{t("cashflow.filterAll")}</Button>
                        <Button variant="ghost" size="sm" onClick={() => setFilter('in')} className={cn("h-7 px-3 text-xs", filter === 'in' ? "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20" : "text-muted-foreground hover:text-emerald-400")}>{t("cashflow.filterInflows")}</Button>
                        <Button variant="ghost" size="sm" onClick={() => setFilter('out')} className={cn("h-7 px-3 text-xs", filter === 'out' ? "bg-rose-500/20 text-rose-400 hover:bg-rose-500/20" : "text-muted-foreground hover:text-rose-400")}>{t("cashflow.filterOutflows")}</Button>
                    </div>
                </div>

                {loading ? (
                    <div className="p-16 text-center text-muted-foreground animate-pulse">{t("cashflow.analyzingFlows")}</div>
                ) : visibleEvents.length === 0 ? (
                    <div className="p-16 text-center">
                        <CalendarDays className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                        <p className="text-muted-foreground">{t("cashflow.emptyState")}</p>
                    </div>
                ) : (
                    <div className="divide-y divide-border max-h-[600px] overflow-y-auto custom-scrollbar">
                        {visibleEvents.map((evt, idx) => (
                            <div key={idx} className="p-4 flex items-center gap-4 hover:bg-accent/50 transition-colors">
                                <div className={cn("w-10 h-10 rounded-full flex items-center justify-center shrink-0 border",
                                    evt.type === 'in' ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-500" : "bg-rose-500/10 border-rose-500/20 text-rose-500")}>
                                    {evt.type === 'in' ? <ArrowUpRight className="w-5 h-5" /> : <ArrowDownRight className="w-5 h-5" />}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-1">
                                        <p className="font-semibold text-foreground truncate">{evt.description}</p>
                                        <span className="text-xs bg-muted text-muted-foreground px-2 py-0.5 rounded font-mono">{evt.ref}</span>
                                    </div>
                                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                                        <span className="flex items-center gap-1.5">
                                            <CalendarDays className="w-3.5 h-3.5" />
                                            {evt.date.toLocaleDateString('es-ES', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' })}
                                        </span>
                                    </div>
                                </div>
                                <div className={cn("font-bold text-lg whitespace-nowrap", evt.type === 'in' ? "text-emerald-400" : "text-rose-400")}>
                                    {evt.type === 'in' ? '+' : '-'}{evt.amount.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </PageContainer>
    );
}
