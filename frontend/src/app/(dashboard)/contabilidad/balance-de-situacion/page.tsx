"use client";

import { useState } from "react";
import { Wallet, TrendingUp, TrendingDown, ChevronDown, ChevronRight, Loader2, Scale } from "lucide-react";
import { cn } from "@/lib/utils";
import { useBalanceSituacion, type AccountBalance } from "./_hooks/useBalanceSituacion";

const fmt = (v: number) => v.toLocaleString("es-ES", { style: "currency", currency: "EUR" });

function SectionBlock({ title, items, totalLabel, total, color }: {
    title: string;
    items: { subsection: string; accounts: AccountBalance[] }[];
    totalLabel: string;
    total: number;
    color: "blue" | "orange" | "emerald";
}) {
    const [expanded, setExpanded] = useState<Record<string, boolean>>({});
    const colors = {
        blue: { header: "text-blue-400 border-blue-500/30", total: "text-blue-400", dot: "bg-blue-400" },
        orange: { header: "text-orange-400 border-orange-500/30", total: "text-orange-400", dot: "bg-orange-400" },
        emerald: { header: "text-emerald-400 border-emerald-500/30", total: "text-emerald-400", dot: "bg-emerald-400" },
    };
    const c = colors[color];

    return (
        <div className="bg-card border border-border rounded-2xl overflow-hidden">
            <div className={cn("px-5 py-4 border-b border-border flex items-center justify-between")}>
                <h3 className={cn("font-bold text-lg flex items-center gap-2", c.header.split(" ")[0])}>
                    <span className={cn("w-2 h-2 rounded-full", c.dot)} />
                    {title}
                </h3>
                <span className={cn("font-bold text-lg", c.total)}>{fmt(total)}</span>
            </div>

            {items.map(({ subsection, accounts }) => {
                const subTotal = accounts.reduce((s, a) => s + a.saldo, 0);
                if (Math.abs(subTotal) < 0.01 && accounts.every(a => Math.abs(a.saldo) < 0.01)) return null;
                const isOpen = expanded[subsection] ?? false;

                return (
                    <div key={subsection} className="border-b border-border/50 last:border-b-0">
                        <button
                            onClick={() => setExpanded(prev => ({ ...prev, [subsection]: !prev[subsection] }))}
                            className="w-full flex items-center justify-between px-5 py-3 hover:bg-accent/50 transition-colors text-left"
                        >
                            <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                                {isOpen ? <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" /> : <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />}
                                {subsection}
                            </div>
                            <span className="text-sm font-semibold text-foreground">{fmt(subTotal)}</span>
                        </button>

                        {isOpen && (
                            <div className="bg-muted/50 divide-y divide-border">
                                {accounts.map(acc => (
                                    <div key={acc.code} className="flex items-center justify-between px-8 py-2.5">
                                        <div className="flex items-center gap-3">
                                            <span className="font-mono text-[11px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">{acc.code}</span>
                                            <span className="text-sm text-muted-foreground">{acc.name}</span>
                                        </div>
                                        <span className="text-sm text-foreground">{fmt(acc.saldo)}</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                );
            })}

            <div className={cn("px-5 py-3 bg-muted flex items-center justify-between border-t border-border")}>
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{totalLabel}</span>
                <span className={cn("text-base font-bold", c.total)}>{fmt(total)}</span>
            </div>
        </div>
    );
}

export default function BalanceSituacionPage() {
    const {
        loading, isEmpty,
        activoItems, pasivoItems, pnItems,
        totalActivo, totalPasivo, totalPN, totalPasivoPN,
        resultadoEjercicio,
    } = useBalanceSituacion();

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-foreground mb-2 flex items-center gap-3">
                        <div className="p-2 bg-blue-500/10 rounded-xl">
                            <Scale className="w-7 h-7 text-blue-400" />
                        </div>
                        Balance de Situación
                    </h1>
                    <p className="text-muted-foreground ml-14">Estado patrimonial según PGC español — Activo = Pasivo + Patrimonio Neto</p>
                </div>

                {!loading && !isEmpty && (
                    <div className={cn(
                        "px-5 py-3 rounded-2xl border text-sm font-semibold flex items-center gap-2",
                        Math.abs(totalActivo - totalPasivoPN) < 1
                            ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                            : "bg-amber-500/10 border-amber-500/20 text-amber-400"
                    )}>
                        <Scale className="w-4 h-4" />
                        {Math.abs(totalActivo - totalPasivoPN) < 1 ? "Balance equilibrado ✓" : `Diferencia: ${fmt(Math.abs(totalActivo - totalPasivoPN))}`}
                    </div>
                )}
            </div>

            {loading ? (
                <div className="flex items-center justify-center py-24">
                    <Loader2 className="w-8 h-8 text-muted-foreground animate-spin" />
                </div>
            ) : isEmpty ? (
                <div className="py-20 text-center bg-card border border-border rounded-2xl">
                    <Scale className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                    <p className="text-muted-foreground font-medium">Sin apuntes contables</p>
                    <p className="text-muted-foreground text-sm mt-1">El Balance de Situación se construye a partir del libro diario.</p>
                </div>
            ) : (
                <>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="bg-card border border-blue-500/20 rounded-2xl p-5 relative overflow-hidden">
                            <div className="absolute top-0 right-0 p-4 opacity-5"><TrendingUp className="w-20 h-20 text-blue-400" /></div>
                            <p className="text-xs font-semibold text-blue-400/70 uppercase tracking-wider mb-2">Total Activo</p>
                            <p className="text-3xl font-bold text-blue-400">{fmt(totalActivo)}</p>
                            <p className="text-xs text-muted-foreground mt-1">Bienes y derechos de la empresa</p>
                        </div>
                        <div className="bg-card border border-orange-500/20 rounded-2xl p-5 relative overflow-hidden">
                            <div className="absolute top-0 right-0 p-4 opacity-5"><TrendingDown className="w-20 h-20 text-orange-400" /></div>
                            <p className="text-xs font-semibold text-orange-400/70 uppercase tracking-wider mb-2">Total Pasivo</p>
                            <p className="text-3xl font-bold text-orange-400">{fmt(totalPasivo)}</p>
                            <p className="text-xs text-muted-foreground mt-1">Deudas y obligaciones</p>
                        </div>
                        <div className="bg-card border border-emerald-500/20 rounded-2xl p-5 relative overflow-hidden">
                            <div className="absolute top-0 right-0 p-4 opacity-5"><Wallet className="w-20 h-20 text-emerald-400" /></div>
                            <p className="text-xs font-semibold text-emerald-400/70 uppercase tracking-wider mb-2">Patrimonio Neto</p>
                            <p className={cn("text-3xl font-bold", totalPN >= 0 ? "text-emerald-400" : "text-red-400")}>{fmt(totalPN)}</p>
                            <p className="text-xs text-muted-foreground mt-1">Incl. resultado {fmt(resultadoEjercicio)}</p>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                        <div className="space-y-4">
                            <SectionBlock title="ACTIVO" items={activoItems} totalLabel="Total Activo" total={totalActivo} color="blue" />
                        </div>
                        <div className="space-y-4">
                            <SectionBlock
                                title="PATRIMONIO NETO"
                                items={[
                                    ...pnItems,
                                    {
                                        subsection: "Resultado del ejercicio",
                                        accounts: [{
                                            code: "129",
                                            name: "Resultado del ejercicio",
                                            saldo: resultadoEjercicio,
                                            side: "patrimonio",
                                            section: "Patrimonio Neto",
                                            subsection: "Resultado del ejercicio",
                                        }],
                                    },
                                ]}
                                totalLabel="Total Patrimonio Neto"
                                total={totalPN}
                                color="emerald"
                            />
                            <SectionBlock title="PASIVO" items={pasivoItems} totalLabel="Total Pasivo" total={totalPasivo} color="orange" />
                            <div className="flex items-center justify-between px-5 py-4 bg-card border border-border rounded-2xl">
                                <span className="text-sm font-bold text-foreground uppercase tracking-wider">Total Pasivo + Patrimonio Neto</span>
                                <span className="text-lg font-bold text-foreground">{fmt(totalPasivoPN)}</span>
                            </div>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
