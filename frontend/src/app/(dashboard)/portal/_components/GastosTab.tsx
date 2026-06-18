"use client";
import { Receipt, Plus, Download, Loader2, Upload } from "lucide-react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import type { Expense } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { EXPENSE_STATUS_STYLE, fmt } from "./constants";

interface GastosTabProps {
    myExpenses: Expense[];
    readOnly: boolean;
    uploadingReceiptId: string | null;
    onNewExpense: () => void;
    onUploadReceipt: (expId: string, file: File) => void;
}

export function GastosTab({ myExpenses, readOnly, uploadingReceiptId, onNewExpense, onUploadReceipt }: GastosTabProps) {
    const t = useTranslations("portal");
    return (
        <div className="space-y-4">
            <div className="flex items-start justify-between gap-4">
                <p className="text-xs text-muted-foreground max-w-xl">
                    {t("gastos.intro")}
                </p>
                <Button size="sm" className="gap-2 shrink-0" disabled={readOnly} onClick={onNewExpense}>
                    <Plus className="w-4 h-4" /> {t("gastos.newExpense")}
                </Button>
            </div>
            {myExpenses.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground">
                    <Receipt className="w-8 h-8 opacity-30" />
                    <p className="text-sm">{t("gastos.emptyTitle")}</p>
                    <p className="text-xs max-w-xs text-center">
                        {t.rich("gastos.emptyHint", { strong: (chunks) => <strong>{chunks}</strong> })}
                    </p>
                </div>
            ) : (
                <div className="rounded-xl border border-border overflow-hidden">
                    <table className="w-full text-sm">
                        <thead className="bg-muted/30 text-muted-foreground">
                            <tr>
                                <th className="text-left px-4 py-3 font-medium">{t("gastos.colCategory")}</th>
                                <th className="text-left px-4 py-3 font-medium">{t("gastos.colDescription")}</th>
                                <th className="text-left px-4 py-3 font-medium">{t("gastos.colDate")}</th>
                                <th className="text-right px-4 py-3 font-medium">{t("gastos.colAmount")}</th>
                                <th className="text-left px-4 py-3 font-medium">{t("gastos.colStatus")}</th>
                                <th className="text-left px-4 py-3 font-medium">{t("gastos.colReceipt")}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                            {myExpenses.map((exp) => (
                                <tr key={exp.id} className="bg-card hover:bg-muted/20 transition-colors">
                                    <td className="px-4 py-3 text-muted-foreground capitalize">
                                        {t.has(`expenseCategories.${exp.category}`) ? t(`expenseCategories.${exp.category}`) : exp.category}
                                    </td>
                                    <td className="px-4 py-3 text-foreground max-w-[180px] truncate" title={exp.description}>
                                        {exp.description}
                                    </td>
                                    <td className="px-4 py-3 text-muted-foreground">{fmt(exp.date)}</td>
                                    <td className="px-4 py-3 text-right font-semibold text-foreground tabular-nums">
                                        {new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(exp.amount)}
                                    </td>
                                    <td className="px-4 py-3">
                                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${EXPENSE_STATUS_STYLE[exp.status] ?? ""}`}>
                                            {t.has(`expenseStatus.${exp.status}`) ? t(`expenseStatus.${exp.status}`) : exp.status}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3">
                                        {exp.receipt_filename ? (
                                            <button
                                                onClick={() => api.hr.expenses.downloadReceipt(exp.id, exp.receipt_filename!)}
                                                className="flex items-center gap-1 text-xs text-primary hover:underline"
                                            >
                                                <Download className="w-3 h-3" /> {t("gastos.view")}
                                            </button>
                                        ) : exp.status === "pending" && !readOnly ? (
                                            <label className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground cursor-pointer">
                                                {uploadingReceiptId === exp.id
                                                    ? <Loader2 className="w-3 h-3 animate-spin" />
                                                    : <Upload className="w-3 h-3" />}
                                                <span>{t("gastos.attach")}</span>
                                                <input
                                                    type="file"
                                                    className="hidden"
                                                    accept=".pdf,.jpg,.jpeg,.png"
                                                    onChange={(e) => {
                                                        const f = e.target.files?.[0];
                                                        if (f) onUploadReceipt(exp.id, f);
                                                    }}
                                                />
                                            </label>
                                        ) : <span className="text-xs text-muted-foreground">—</span>}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
