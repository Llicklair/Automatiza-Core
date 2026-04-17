"use client";

import { TrendingUp, TrendingDown, Wallet } from "lucide-react";

interface KpiSectionProps {
    loading: boolean;
    summary: { ingresos: number; gastos: number; neto: number; margen: number };
}

export function KpiSection({ loading, summary }: KpiSectionProps) {
    const netoIsPositive = summary.neto >= 0;

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Ingresos */}
            <div className="rounded-2xl border border-emerald-500/20 bg-gradient-to-br from-card to-emerald-950/20 p-6 relative overflow-hidden group">
                <div className="absolute -right-4 -top-4 w-24 h-24 bg-emerald-500/10 rounded-full blur-2xl group-hover:bg-emerald-500/20 transition-all duration-500"></div>
                <div className="flex items-center gap-3 mb-4 relative">
                    <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                        <TrendingUp className="w-5 h-5 text-emerald-400" />
                    </div>
                    <h3 className="text-sm font-medium text-emerald-400/80">Ingresos (30d)</h3>
                </div>
                <div className="text-4xl font-bold text-foreground tracking-tight relative">
                    {loading ? "\u2014" : `${summary.ingresos.toLocaleString('es-ES', { minimumFractionDigits: 2 })}\u20AC`}
                </div>
            </div>

            {/* Gastos */}
            <div className="rounded-2xl border border-red-500/20 bg-gradient-to-br from-card to-red-950/20 p-6 relative overflow-hidden group">
                <div className="absolute -right-4 -top-4 w-24 h-24 bg-red-500/10 rounded-full blur-2xl group-hover:bg-red-500/20 transition-all duration-500"></div>
                <div className="flex items-center gap-3 mb-4 relative">
                    <div className="w-10 h-10 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
                        <TrendingDown className="w-5 h-5 text-red-400" />
                    </div>
                    <h3 className="text-sm font-medium text-red-400/80">Gastos (30d)</h3>
                </div>
                <div className="text-4xl font-bold text-foreground tracking-tight relative">
                    {loading ? "\u2014" : `${Math.abs(summary.gastos).toLocaleString('es-ES', { minimumFractionDigits: 2 })}\u20AC`}
                </div>
            </div>

            {/* Beneficio */}
            <div className={`rounded-2xl border ${netoIsPositive ? 'border-primary/20 bg-gradient-to-br from-card to-indigo-900/20' : 'border-amber-500/30 bg-gradient-to-br from-card to-amber-900/20'} p-6 relative overflow-hidden group shadow-lg shadow-black/50`}>
                <div className={`absolute -right-4 -top-4 w-32 h-32 ${netoIsPositive ? 'bg-primary/10' : 'bg-amber-500/10'} rounded-full blur-3xl group-hover:scale-110 transition-transform duration-700`}></div>
                <div className="flex items-center justify-between mb-4 relative">
                    <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-xl ${netoIsPositive ? 'bg-primary/20 border-primary/20' : 'bg-amber-500/20 border-amber-500/30'} border flex items-center justify-center`}>
                            <Wallet className={`w-5 h-5 ${netoIsPositive ? 'text-primary' : 'text-amber-400'}`} />
                        </div>
                        <h3 className={`text-sm font-medium ${netoIsPositive ? 'text-primary' : 'text-amber-300'}`}>Beneficio Neto</h3>
                    </div>
                    {!loading && (
                        <span className={`text-xs px-2.5 py-1 rounded-full font-bold border ${netoIsPositive ? 'bg-primary/10 text-primary border-primary/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'}`}>
                            {summary.margen > 0 ? '+' : ''}{summary.margen}% Margen
                        </span>
                    )}
                </div>
                <div className="text-4xl font-bold text-foreground tracking-tight relative">
                    {loading ? "\u2014" : `${summary.neto.toLocaleString('es-ES', { minimumFractionDigits: 2 })}\u20AC`}
                </div>
            </div>
        </div>
    );
}
