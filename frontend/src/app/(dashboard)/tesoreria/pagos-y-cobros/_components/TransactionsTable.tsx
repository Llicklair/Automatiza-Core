import type { BankTransaction } from "@/lib/api";
import { Banknote, CheckCircle2, Clock, Loader2, RefreshCw } from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

const fmt = (v: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(v);

interface TransactionsTableProps {
    transactions: BankTransaction[];
    syncing: boolean;
    onSync: () => void;
}

export default function TransactionsTable({ transactions, syncing, onSync }: TransactionsTableProps) {
    const t = useTranslations("tesoreria");

    if (transactions.length === 0) {
        return (
            <div className="py-16 text-center">
                <Banknote className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
                <p className="text-muted-foreground font-medium">{t("transactionsTable.emptyTitle")}</p>
                <p className="text-xs text-muted-foreground mt-1">{t("transactionsTable.emptyDescription")}</p>
                <button onClick={onSync} disabled={syncing} className="mt-4 flex items-center gap-2 mx-auto px-4 py-2 bg-blue-600 hover:bg-blue-500 text-foreground text-sm font-medium rounded-xl transition-colors">
                    {syncing ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                    {t("transactionsTable.syncNow")}
                </button>
            </div>
        );
    }

    return (
        <table className="w-full text-left text-sm">
            <thead className="bg-muted/50 text-muted-foreground border-b border-border">
                <tr>
                    <th className="px-6 py-3 font-medium">{t("transactionsTable.colDate")}</th>
                    <th className="px-6 py-3 font-medium">{t("transactionsTable.colConcept")}</th>
                    <th className="px-6 py-3 font-medium text-right">{t("transactionsTable.colAmount")}</th>
                    <th className="px-6 py-3 font-medium text-right">{t("transactionsTable.colBalance")}</th>
                    <th className="px-6 py-3 font-medium">{t("transactionsTable.colStatus")}</th>
                </tr>
            </thead>
            <tbody className="divide-y divide-border">
                {transactions.map(tx => (
                    <tr key={tx.id} className="hover:bg-blue-500/[0.02] transition-colors">
                        <td className="px-6 py-4 text-xs text-muted-foreground whitespace-nowrap">
                            {format(new Date(tx.date), "d MMM yyyy", { locale: es })}
                        </td>
                        <td className="px-6 py-4 text-foreground">{tx.description}</td>
                        <td className={cn("px-6 py-4 text-right font-semibold", tx.amount >= 0 ? "text-emerald-400" : "text-red-400")}>
                            {tx.amount >= 0 ? "+" : ""}{fmt(tx.amount)}
                        </td>
                        <td className="px-6 py-4 text-right text-foreground text-xs">
                            {tx.balance != null ? fmt(tx.balance) : "—"}
                        </td>
                        <td className="px-6 py-4">
                            {tx.status === "reconciled" ? (
                                <span className="flex items-center gap-1 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                                    <CheckCircle2 className="w-3 h-3" /> {t("transactionsTable.statusReconciled")}
                                </span>
                            ) : (
                                <span className="flex items-center gap-1 text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full">
                                    <Clock className="w-3 h-3" /> {t("transactionsTable.statusPending")}
                                </span>
                            )}
                        </td>
                    </tr>
                ))}
            </tbody>
        </table>
    );
}
