"use client";

import { useEffect, useState } from "react";
import { api, type JournalEntry } from "@/lib/api";
import { logError } from "@/lib/logger";
import { TrendingUp, TrendingDown, Wallet, BookOpen, Loader2 } from "lucide-react";

const fmt = (n: number) => n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });
const pct = (n: number, total: number) => total === 0 ? "—" : `${((n / total) * 100).toFixed(1)}%`;

// Spanish PGC account names for group 6 & 7
const ACCOUNT_NAMES: Record<string, string> = {
    "600": "Compras de mercaderías",
    "601": "Compras de materias primas",
    "602": "Compras de otros aprovisionamientos",
    "606": "Descuentos sobre compras",
    "610": "Variación de existencias de mercaderías",
    "620": "Gastos en investigación y desarrollo",
    "621": "Arrendamientos y cánones",
    "622": "Reparaciones y conservación",
    "623": "Servicios de profesionales independientes",
    "624": "Transportes",
    "625": "Primas de seguros",
    "626": "Servicios bancarios y similares",
    "627": "Publicidad, propaganda y relaciones públicas",
    "628": "Suministros (luz, agua, internet)",
    "629": "Otros servicios",
    "630": "Impuesto sobre beneficios",
    "640": "Sueldos y salarios",
    "641": "Indemnizaciones",
    "642": "Seguridad Social a cargo de la empresa",
    "649": "Otros gastos sociales",
    "650": "Pérdidas de créditos comerciales incobrables",
    "660": "Gastos financieros",
    "681": "Amortización del inmovilizado material",
    "682": "Amortización del inmovilizado intangible",
    "700": "Ventas de mercaderías",
    "701": "Ventas de productos terminados",
    "702": "Ventas de productos semiterminados",
    "703": "Ventas de subproductos y residuos",
    "704": "Ventas de envases y embalajes",
    "705": "Prestaciones de servicios",
    "706": "Descuentos sobre ventas",
    "708": "Devoluciones de ventas",
    "709": "Rappels sobre ventas",
    "740": "Subvenciones, donaciones y legados",
    "746": "Subvenciones, donaciones y legados transferidos al resultado",
    "751": "Resultados de operaciones en común",
    "760": "Ingresos de participaciones en instrumentos de patrimonio",
    "761": "Ingresos de valores representativos de deuda",
    "762": "Ingresos de créditos",
    "769": "Otros ingresos financieros",
    "790": "Reversión del deterioro de activos",
};

export default function PyGPage() {
    const [entries, setEntries] = useState<JournalEntry[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.accounting.journal.list()
            .then(setEntries)
            .catch(err => logError("contabilidad/pyl", err))
            .finally(() => setLoading(false));
    }, []);

    // Build account balances from journal lines
    const balances: Record<string, { name: string; debit: number; credit: number; group: string }> = {};
    entries.forEach(entry => {
        entry.lines.forEach(line => {
            const g = line.account_code.substring(0, 1);
            if (!["6", "7"].includes(g)) return;
            const code3 = line.account_code.substring(0, 3);
            if (!balances[code3]) {
                balances[code3] = {
                    name: ACCOUNT_NAMES[code3] || line.account_name || `Cuenta ${code3}`,
                    debit: 0, credit: 0, group: g,
                };
            }
            balances[code3].debit += Number(line.debit);
            balances[code3].credit += Number(line.credit);
        });
    });

    const incomeAccounts = Object.entries(balances)
        .filter(([_, b]) => b.group === "7")
        .sort(([a], [b]) => a.localeCompare(b));
    const expenseAccounts = Object.entries(balances)
        .filter(([_, b]) => b.group === "6")
        .sort(([a], [b]) => a.localeCompare(b));

    const totalIncome = incomeAccounts.reduce((acc, [_, b]) => acc + (b.credit - b.debit), 0);
    const totalExpense = expenseAccounts.reduce((acc, [_, b]) => acc + (b.debit - b.credit), 0);
    const result = totalIncome - totalExpense;
    const margin = totalIncome > 0 ? ((result / totalIncome) * 100).toFixed(1) : "0.0";

    const noData = !loading && entries.length === 0;

    return (
        <div className="p-8 max-w-6xl mx-auto space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white tracking-tight">Pérdidas y Ganancias</h1>
                    <p className="mt-1 text-sm text-zinc-400">
                        Cuenta de explotación calculada desde el libro diario (cuentas 6 y 7).
                    </p>
                </div>
                {noData && (
                    <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs px-3 py-2 rounded-xl">
                        <BookOpen className="w-4 h-4" />
                        Sin asientos — registra facturas para ver la P&amp;G real
                    </div>
                )}
            </div>

            {loading ? (
                <div className="flex items-center justify-center py-24 text-zinc-500 gap-2">
                    <Loader2 className="w-5 h-5 animate-spin" /> Cargando datos contables…
                </div>
            ) : (
                <>
                    {/* KPIs */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                        <div className="bg-[#111113] border border-[#27272a] p-6 rounded-2xl relative overflow-hidden">
                            <div className="absolute top-0 right-0 p-4 opacity-10"><TrendingUp className="w-20 h-20 text-emerald-500" /></div>
                            <p className="text-xs text-zinc-500 font-semibold uppercase tracking-wider mb-2">Ingresos</p>
                            <p className="text-2xl font-bold text-emerald-400">{fmt(totalIncome)}</p>
                            <p className="text-xs text-zinc-600 mt-2">Grupo 7 — Ventas y servicios</p>
                        </div>
                        <div className="bg-[#111113] border border-[#27272a] p-6 rounded-2xl relative overflow-hidden">
                            <div className="absolute top-0 right-0 p-4 opacity-10"><TrendingDown className="w-20 h-20 text-rose-500" /></div>
                            <p className="text-xs text-zinc-500 font-semibold uppercase tracking-wider mb-2">Gastos</p>
                            <p className="text-2xl font-bold text-rose-400">{fmt(totalExpense)}</p>
                            <p className="text-xs text-zinc-600 mt-2">Grupo 6 — Compras y gastos</p>
                        </div>
                        <div className="bg-[#111113] border border-[#27272a] p-6 rounded-2xl">
                            <p className="text-xs text-zinc-500 font-semibold uppercase tracking-wider mb-2">Margen</p>
                            <p className="text-2xl font-bold text-blue-400">{margin}%</p>
                            <p className="text-xs text-zinc-600 mt-2">Resultado / Ingresos</p>
                        </div>
                        <div className={`p-6 rounded-2xl border ${result >= 0 ? "bg-emerald-500/10 border-emerald-500/20" : "bg-rose-500/10 border-rose-500/20"}`}>
                            <p className={`text-xs font-semibold uppercase tracking-wider mb-2 ${result >= 0 ? "text-emerald-400" : "text-rose-400"}`}>Resultado Neto</p>
                            <p className={`text-2xl font-bold ${result >= 0 ? "text-emerald-400" : "text-rose-400"}`}>{fmt(result)}</p>
                            <div className="flex items-center gap-1 mt-2 text-xs text-zinc-500">
                                <Wallet className="w-3 h-3" /> Ejercicio actual
                            </div>
                        </div>
                    </div>

                    {/* Detalle analítico */}
                    <div className="bg-[#111113] border border-[#27272a] rounded-2xl overflow-hidden shadow-xl shadow-black/20">
                        <div className="px-8 py-5 border-b border-[#27272a]">
                            <h3 className="text-base font-bold text-white">Detalle Analítico</h3>
                        </div>
                        <div className="p-8 space-y-8 text-sm">
                            {/* Ingresos */}
                            <div>
                                <div className="flex items-center mb-3">
                                    <span className="flex-1 font-semibold text-emerald-400 uppercase tracking-wide text-xs">1. Ingresos de explotación (Grupo 7)</span>
                                    <span className="font-mono font-semibold text-emerald-400">{fmt(totalIncome)}</span>
                                    <span className="w-20 text-right text-zinc-500">100%</span>
                                </div>
                                {incomeAccounts.length === 0 ? (
                                    <p className="text-zinc-600 italic text-xs pl-4">Sin apuntes de ingresos registrados</p>
                                ) : (
                                    <div className="pl-4 space-y-2 border-l border-[#27272a] ml-2">
                                        {incomeAccounts.map(([code, b]) => {
                                            const amount = b.credit - b.debit;
                                            return (
                                                <div key={code} className="flex items-center text-zinc-400">
                                                    <span className="font-mono text-xs text-zinc-600 w-10">{code}</span>
                                                    <span className="flex-1 ml-3">{b.name}</span>
                                                    <span className="font-mono text-zinc-300">{fmt(amount)}</span>
                                                    <span className="w-20 text-right text-zinc-600 text-xs">{pct(amount, totalIncome)}</span>
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>

                            {/* Gastos */}
                            <div>
                                <div className="flex items-center mb-3">
                                    <span className="flex-1 font-semibold text-rose-400 uppercase tracking-wide text-xs">2. Gastos de explotación (Grupo 6)</span>
                                    <span className="font-mono font-semibold text-rose-400">-{fmt(totalExpense)}</span>
                                    <span className="w-20 text-right text-zinc-500">{pct(totalExpense, totalIncome)}</span>
                                </div>
                                {expenseAccounts.length === 0 ? (
                                    <p className="text-zinc-600 italic text-xs pl-4">Sin apuntes de gastos registrados</p>
                                ) : (
                                    <div className="pl-4 space-y-2 border-l border-[#27272a] ml-2">
                                        {expenseAccounts.map(([code, b]) => {
                                            const amount = b.debit - b.credit;
                                            return (
                                                <div key={code} className="flex items-center text-zinc-400">
                                                    <span className="font-mono text-xs text-zinc-600 w-10">{code}</span>
                                                    <span className="flex-1 ml-3">{b.name}</span>
                                                    <span className="font-mono text-zinc-300">-{fmt(amount)}</span>
                                                    <span className="w-20 text-right text-zinc-600 text-xs">{pct(amount, totalIncome)}</span>
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>

                            {/* Resultado */}
                            <div className="flex items-center pt-4 border-t border-[#27272a]">
                                <span className="flex-1 font-bold text-white uppercase tracking-wider">Resultado de Explotación</span>
                                <span className={`font-bold font-mono text-base ${result >= 0 ? "text-emerald-400" : "text-rose-400"}`}>{fmt(result)}</span>
                                <span className="w-20 text-right text-zinc-500">{margin}%</span>
                            </div>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
