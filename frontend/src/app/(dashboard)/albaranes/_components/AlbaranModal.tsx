"use client";

import { useTranslations } from "next-intl";
import { X, Plus, Loader2, CheckCircle2 } from "lucide-react";
import type { LineForm } from "../_hooks/useAlbaranes";
import { emptyLine } from "../_hooks/useAlbaranes";

interface Props {
    saving: boolean;
    clientName: string;
    setClientName: (v: string) => void;
    date: string;
    setDate: (v: string) => void;
    notes: string;
    setNotes: (v: string) => void;
    lines: LineForm[];
    setLines: React.Dispatch<React.SetStateAction<LineForm[]>>;
    onClose: () => void;
    onSubmit: (e: React.FormEvent) => void;
}

export function AlbaranModal({ saving, clientName, setClientName, date, setDate, notes, setNotes, lines, setLines, onClose, onSubmit }: Props) {
    const t = useTranslations("albaranes");
    const tc = useTranslations("common");
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-card border border-border rounded-2xl w-full max-w-3xl shadow-2xl flex flex-col max-h-[90vh]">
                <div className="flex items-center justify-between p-6 border-b border-border">
                    <h3 className="text-xl font-bold text-foreground">{t("modal.title")}</h3>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition" aria-label={tc("close")}>
                        <X className="w-5 h-5" aria-hidden="true" />
                    </button>
                </div>
                <form onSubmit={onSubmit} className="flex-1 overflow-auto p-6 space-y-5">
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-xs text-muted-foreground mb-1">{t("modal.client")}</label>
                            <input value={clientName} onChange={e => setClientName(e.target.value)}
                                placeholder={t("modal.clientPlaceholder")}
                                className="w-full px-3 py-2 rounded-lg bg-muted border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50" />
                        </div>
                        <div>
                            <label className="block text-xs text-muted-foreground mb-1">{t("modal.date")}</label>
                            <input type="date" value={date} onChange={e => setDate(e.target.value)}
                                className="w-full px-3 py-2 rounded-lg bg-muted border border-border text-sm text-foreground focus:outline-none focus:border-primary/50" />
                        </div>
                    </div>

                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <label className="text-xs text-muted-foreground">{t("modal.lines")}</label>
                            <button type="button" onClick={() => setLines(prev => [...prev, emptyLine()])}
                                className="text-xs text-primary hover:text-primary flex items-center gap-1 transition">
                                <Plus className="w-3 h-3" /> {t("modal.addLine")}
                            </button>
                        </div>
                        <div className="space-y-2">
                            <div className="grid grid-cols-12 gap-2 text-[10px] text-muted-foreground px-1">
                                <span className="col-span-5">{t("modal.colDescription")}</span>
                                <span className="col-span-2">{t("modal.colQuantity")}</span>
                                <span className="col-span-2">{t("modal.colUnitPrice")}</span>
                                <span className="col-span-2">{t("modal.colTax")}</span>
                                <span className="col-span-1"></span>
                            </div>
                            {lines.map((line, i) => (
                                <div key={i} className="grid grid-cols-12 gap-2 items-center">
                                    <input value={line.description} onChange={e => setLines(prev => prev.map((l, j) => j === i ? { ...l, description: e.target.value } : l))}
                                        placeholder={t("modal.descriptionPlaceholder")} className="col-span-5 px-2 py-1.5 rounded-lg bg-muted border border-border text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50" />
                                    <input type="number" value={line.quantity} onChange={e => setLines(prev => prev.map((l, j) => j === i ? { ...l, quantity: e.target.value } : l))}
                                        className="col-span-2 px-2 py-1.5 rounded-lg bg-muted border border-border text-xs text-foreground focus:outline-none focus:border-primary/50" />
                                    <input type="number" value={line.unit_price} onChange={e => setLines(prev => prev.map((l, j) => j === i ? { ...l, unit_price: e.target.value } : l))}
                                        className="col-span-2 px-2 py-1.5 rounded-lg bg-muted border border-border text-xs text-foreground focus:outline-none focus:border-primary/50" />
                                    <input type="number" value={line.tax_percentage} onChange={e => setLines(prev => prev.map((l, j) => j === i ? { ...l, tax_percentage: e.target.value } : l))}
                                        className="col-span-2 px-2 py-1.5 rounded-lg bg-muted border border-border text-xs text-foreground focus:outline-none focus:border-primary/50" />
                                    <button type="button" onClick={() => lines.length > 1 && setLines(prev => prev.filter((_, j) => j !== i))}
                                        className="col-span-1 flex justify-center text-muted-foreground/60 hover:text-red-400 transition">
                                        <X className="w-3.5 h-3.5" />
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div>
                        <label className="block text-xs text-muted-foreground mb-1">{t("modal.notes")}</label>
                        <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={2}
                            placeholder={t("modal.notesPlaceholder")}
                            className="w-full px-3 py-2 rounded-lg bg-muted border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50 resize-none" />
                    </div>

                    <div className="flex justify-end gap-3 pt-2">
                        <button type="button" onClick={onClose}
                            className="px-4 py-2 rounded-lg bg-muted hover:bg-accent text-foreground text-sm transition">
                            {tc("cancel")}
                        </button>
                        <button type="submit" disabled={saving}
                            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary hover:bg-primary disabled:opacity-50 text-foreground text-sm font-medium transition">
                            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                            {t("modal.submit")}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
