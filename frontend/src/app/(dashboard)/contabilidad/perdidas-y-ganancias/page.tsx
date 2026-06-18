"use client";

import { TrendingUp, TrendingDown, Wallet, BookOpen, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { usePyG } from "./_hooks/usePyG";

const fmt = (n: number) => n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });
const pct = (n: number, total: number) => total === 0 ? "—" : `${((n / total) * 100).toFixed(1)}%`;

export default function PyGPage() {
    const t = useTranslations("contabilidad");
    const { loading, noData, incomeAccounts, expenseAccounts, totalIncome, totalExpense, result, margin } = usePyG();

    return (
        <div className="p-8 max-w-6xl mx-auto space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-foreground tracking-tight">{t("pyg.title")}</h1>
                    <p className="mt-1 text-sm text-muted-foreground">
                        {t("pyg.subtitle")}
                    </p>
                </div>
                {noData && (
                    <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs px-3 py-2 rounded-xl">
                        <BookOpen className="w-4 h-4" />
                        {t("pyg.noEntries")}
                    </div>
                )}
            </div>

            {loading ? (
                <div className="flex items-center justify-center py-24 text-muted-foreground gap-2">
                    <Loader2 className="w-5 h-5 animate-spin" /> {t("pyg.loading")}
                </div>
            ) : (
                <>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                        <div className="bg-card border border-border p-6 rounded-2xl relative overflow-hidden">
                            <div className="absolute top-0 right-0 p-4 opacity-10"><TrendingUp className="w-20 h-20 text-emerald-500" /></div>
                            <p className="text-xs text-muted-foreground font-semibold uppercase tracking-wider mb-2">{t("pyg.income")}</p>
                            <p className="text-2xl font-bold text-emerald-400">{fmt(totalIncome)}</p>
                            <p className="text-xs text-muted-foreground mt-2">{t("pyg.incomeHint")}</p>
                        </div>
                        <div className="bg-card border border-border p-6 rounded-2xl relative overflow-hidden">
                            <div className="absolute top-0 right-0 p-4 opacity-10"><TrendingDown className="w-20 h-20 text-rose-500" /></div>
                            <p className="text-xs text-muted-foreground font-semibold uppercase tracking-wider mb-2">{t("pyg.expenses")}</p>
                            <p className="text-2xl font-bold text-rose-400">{fmt(totalExpense)}</p>
                            <p className="text-xs text-muted-foreground mt-2">{t("pyg.expensesHint")}</p>
                        </div>
                        <div className="bg-card border border-border p-6 rounded-2xl">
                            <p className="text-xs text-muted-foreground font-semibold uppercase tracking-wider mb-2">{t("pyg.margin")}</p>
                            <p className="text-2xl font-bold text-blue-400">{margin}%</p>
                            <p className="text-xs text-muted-foreground mt-2">{t("pyg.marginHint")}</p>
                        </div>
                        <div className={`p-6 rounded-2xl border ${result >= 0 ? "bg-emerald-500/10 border-emerald-500/20" : "bg-rose-500/10 border-rose-500/20"}`}>
                            <p className={`text-xs font-semibold uppercase tracking-wider mb-2 ${result >= 0 ? "text-emerald-400" : "text-rose-400"}`}>{t("pyg.netResult")}</p>
                            <p className={`text-2xl font-bold ${result >= 0 ? "text-emerald-400" : "text-rose-400"}`}>{fmt(result)}</p>
                            <div className="flex items-center gap-1 mt-2 text-xs text-muted-foreground">
                                <Wallet className="w-3 h-3" /> {t("pyg.currentYear")}
                            </div>
                        </div>
                    </div>

                    <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-xl shadow-black/20">
                        <div className="px-8 py-5 border-b border-border">
                            <h3 className="text-base font-bold text-foreground">{t("pyg.analyticDetail")}</h3>
                        </div>
                        <div className="p-8 space-y-8 text-sm">
                            <div>
                                <div className="flex items-center mb-3">
                                    <span className="flex-1 font-semibold text-emerald-400 uppercase tracking-wide text-xs">{t("pyg.operatingIncome")}</span>
                                    <span className="font-mono font-semibold text-emerald-400">{fmt(totalIncome)}</span>
                                    <span className="w-20 text-right text-muted-foreground">100%</span>
                                </div>
                                {incomeAccounts.length === 0 ? (
                                    <p className="text-muted-foreground italic text-xs pl-4">{t("pyg.noIncomeEntries")}</p>
                                ) : (
                                    <div className="pl-4 space-y-2 border-l border-border ml-2">
                                        {incomeAccounts.map(([code, b]) => {
                                            const amount = b.credit - b.debit;
                                            return (
                                                <div key={code} className="flex items-center text-muted-foreground">
                                                    <span className="font-mono text-xs text-muted-foreground w-10">{code}</span>
                                                    <span className="flex-1 ml-3">{b.name}</span>
                                                    <span className="font-mono text-foreground">{fmt(amount)}</span>
                                                    <span className="w-20 text-right text-muted-foreground text-xs">{pct(amount, totalIncome)}</span>
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>

                            <div>
                                <div className="flex items-center mb-3">
                                    <span className="flex-1 font-semibold text-rose-400 uppercase tracking-wide text-xs">{t("pyg.operatingExpenses")}</span>
                                    <span className="font-mono font-semibold text-rose-400">-{fmt(totalExpense)}</span>
                                    <span className="w-20 text-right text-muted-foreground">{pct(totalExpense, totalIncome)}</span>
                                </div>
                                {expenseAccounts.length === 0 ? (
                                    <p className="text-muted-foreground italic text-xs pl-4">{t("pyg.noExpenseEntries")}</p>
                                ) : (
                                    <div className="pl-4 space-y-2 border-l border-border ml-2">
                                        {expenseAccounts.map(([code, b]) => {
                                            const amount = b.debit - b.credit;
                                            return (
                                                <div key={code} className="flex items-center text-muted-foreground">
                                                    <span className="font-mono text-xs text-muted-foreground w-10">{code}</span>
                                                    <span className="flex-1 ml-3">{b.name}</span>
                                                    <span className="font-mono text-foreground">-{fmt(amount)}</span>
                                                    <span className="w-20 text-right text-muted-foreground text-xs">{pct(amount, totalIncome)}</span>
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>

                            <div className="flex items-center pt-4 border-t border-border">
                                <span className="flex-1 font-bold text-foreground uppercase tracking-wider">{t("pyg.operatingResult")}</span>
                                <span className={`font-bold font-mono text-base ${result >= 0 ? "text-emerald-400" : "text-rose-400"}`}>{fmt(result)}</span>
                                <span className="w-20 text-right text-muted-foreground">{margin}%</span>
                            </div>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
