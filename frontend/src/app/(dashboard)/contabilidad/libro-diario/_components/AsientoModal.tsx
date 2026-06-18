"use client";

import { PlusCircle, Trash2, AlertCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { type JournalLine } from "@/lib/api";
import { type NewEntryState } from "../_hooks/useLibroDiario";

interface Props {
    newEntry: NewEntryState;
    setNewEntry: React.Dispatch<React.SetStateAction<NewEntryState>>;
    totalDebit: number;
    totalCredit: number;
    isBalanced: boolean;
    onClose: () => void;
    onSubmit: (e: React.FormEvent) => void;
    onAddLine: () => void;
    onRemoveLine: (index: number) => void;
    onLineChange: (index: number, field: keyof JournalLine, value: any) => void;
}

export function AsientoModal({
    newEntry, setNewEntry, totalDebit, totalCredit, isBalanced,
    onClose, onSubmit, onAddLine, onRemoveLine, onLineChange,
}: Props) {
    const t = useTranslations("contabilidad");
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-card border border-border rounded-2xl w-full max-w-4xl shadow-2xl p-6 max-h-[90vh] flex flex-col">
                <h3 className="text-xl font-bold text-foreground mb-6">{t("asientoModal.title")}</h3>

                <form onSubmit={onSubmit} className="flex-1 overflow-auto flex flex-col">
                    <div className="grid grid-cols-3 gap-6 mb-8">
                        <div>
                            <label className="block text-sm font-medium text-muted-foreground mb-2">{t("asientoModal.labelDate")}</label>
                            <input required type="date" className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-foreground outline-none focus:border-primary transition-colors"
                                value={newEntry.date} onChange={e => setNewEntry({ ...newEntry, date: e.target.value })} />
                        </div>
                        <div className="col-span-2">
                            <label className="block text-sm font-medium text-muted-foreground mb-2">{t("asientoModal.labelConcept")}</label>
                            <input required type="text" placeholder={t("asientoModal.conceptPlaceholder")} className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-foreground outline-none focus:border-primary transition-colors"
                                value={newEntry.description} onChange={e => setNewEntry({ ...newEntry, description: e.target.value })} />
                        </div>
                    </div>

                    <div className="flex-1">
                        <div className="flex items-center justify-between mb-3">
                            <h4 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">{t("asientoModal.linesTitle")}</h4>
                            <button type="button" onClick={onAddLine} className="text-xs flex items-center gap-1.5 text-primary hover:text-primary font-medium">
                                <PlusCircle className="w-4 h-4" /> {t("asientoModal.addLine")}
                            </button>
                        </div>

                        <div className="bg-muted/50 border border-border rounded-xl overflow-hidden">
                            <table className="w-full text-sm">
                                <thead className="bg-card text-muted-foreground border-b border-border">
                                    <tr>
                                        <th className="px-4 py-3 font-medium text-left w-40">{t("asientoModal.thAccount")}</th>
                                        <th className="px-4 py-3 font-medium text-left">{t("asientoModal.thReference")}</th>
                                        <th className="px-4 py-3 font-medium text-right w-36">{t("asientoModal.thDebit")}</th>
                                        <th className="px-4 py-3 font-medium text-right w-36">{t("asientoModal.thCredit")}</th>
                                        <th className="px-4 py-3 w-12"></th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-border">
                                    {newEntry.lines.map((line, idx) => (
                                        <tr key={idx}>
                                            <td className="p-2">
                                                <input required type="text" placeholder={t("asientoModal.accountPlaceholder")} className="w-full bg-transparent border border-transparent hover:border-border focus:border-primary rounded px-3 py-1.5 text-foreground outline-none transition-colors font-mono"
                                                    value={line.account_code || ''} onChange={e => onLineChange(idx, 'account_code', e.target.value)} />
                                            </td>
                                            <td className="p-2">
                                                <input type="text" placeholder={t("asientoModal.namePlaceholder")} className="w-full bg-transparent border border-transparent hover:border-border focus:border-primary rounded px-3 py-1.5 text-foreground outline-none transition-colors"
                                                    value={line.account_name || ''} onChange={e => onLineChange(idx, 'account_name', e.target.value)} />
                                            </td>
                                            <td className="p-2">
                                                <input type="number" step="0.01" min="0" className="w-full bg-transparent border border-transparent hover:border-border focus:border-emerald-500 rounded px-3 py-1.5 text-emerald-400 font-medium text-right outline-none transition-colors"
                                                    value={line.debit || ''} onChange={e => onLineChange(idx, 'debit', Number(e.target.value))} />
                                            </td>
                                            <td className="p-2">
                                                <input type="number" step="0.01" min="0" className="w-full bg-transparent border border-transparent hover:border-border focus:border-rose-500 rounded px-3 py-1.5 text-rose-400 font-medium text-right outline-none transition-colors"
                                                    value={line.credit || ''} onChange={e => onLineChange(idx, 'credit', Number(e.target.value))} />
                                            </td>
                                            <td className="p-2 text-center">
                                                <button type="button" onClick={() => onRemoveLine(idx)} disabled={newEntry.lines.length <= 2} className="p-1.5 text-muted-foreground hover:text-red-400 hover:bg-red-500/10 rounded transition-colors disabled:opacity-30" aria-label={t("asientoModal.deleteLine")}>
                                                    <Trash2 className="w-4 h-4" aria-hidden="true" />
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                                <tfoot className="bg-card border-t border-border">
                                    <tr>
                                        <td colSpan={2} className="px-4 py-3 text-right font-medium text-muted-foreground">{t("asientoModal.total")}</td>
                                        <td className={cn("px-4 py-3 text-right font-bold text-lg", isBalanced ? "text-emerald-500" : "text-foreground")}>
                                            {totalDebit.toLocaleString('es-ES', { minimumFractionDigits: 2 })}
                                        </td>
                                        <td className={cn("px-4 py-3 text-right font-bold text-lg", isBalanced ? "text-emerald-500" : "text-foreground")}>
                                            {totalCredit.toLocaleString('es-ES', { minimumFractionDigits: 2 })}
                                        </td>
                                        <td></td>
                                    </tr>
                                </tfoot>
                            </table>
                        </div>

                        {!isBalanced && (
                            <div className="mt-4 flex items-center gap-2 text-amber-500 bg-amber-500/10 px-4 py-3 rounded-lg border border-amber-500/20">
                                <AlertCircle className="w-5 h-5 shrink-0" />
                                <span className="text-sm font-medium">{t("asientoModal.unbalanced", { amount: `${Math.abs(totalDebit - totalCredit).toLocaleString('es-ES')} €` })}</span>
                            </div>
                        )}
                    </div>

                    <div className="flex justify-end gap-3 pt-6 mt-6 border-t border-border">
                        <button type="button" onClick={onClose} className="px-6 py-2.5 text-muted-foreground font-medium hover:bg-accent/50 rounded-xl transition-colors">{t("asientoModal.cancel")}</button>
                        <button type="submit" disabled={!isBalanced} className="px-6 py-2.5 bg-primary hover:bg-primary disabled:opacity-50 disabled:hover:bg-primary text-foreground rounded-xl font-medium transition-all shadow-lg shadow-primary/20">{t("asientoModal.submit")}</button>
                    </div>
                </form>
            </div>
        </div>
    );
}
