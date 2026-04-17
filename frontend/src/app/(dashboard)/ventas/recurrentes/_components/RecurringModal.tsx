"use client";

import { type Client, type RecurringLineItem } from "@/lib/api";
import { fmt, type RecurringForm } from "../_hooks/useRecurrentes";
import { Plus, X, Loader2 } from "lucide-react";

interface RecurringModalProps {
    form: RecurringForm;
    setForm: React.Dispatch<React.SetStateAction<RecurringForm>>;
    editingId: string | null;
    clients: Client[];
    saving: boolean;
    lineTotal: (line: RecurringLineItem) => number;
    totalAmount: number;
    onSubmit: (e: React.FormEvent) => void;
    onClose: () => void;
    setLine: (i: number, field: keyof RecurringLineItem, value: any) => void;
    addLine: () => void;
    removeLine: (i: number) => void;
    t: (key: string, params?: any) => string;
    tc: (key: string) => string;
}

export default function RecurringModal({
    form, setForm, editingId, clients, saving,
    lineTotal, totalAmount, onSubmit, onClose,
    setLine, addLine, removeLine, t, tc,
}: RecurringModalProps) {
    return (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 backdrop-blur-sm pt-16 pb-8 overflow-y-auto">
            <div className="bg-card border border-border rounded-2xl p-8 w-full max-w-2xl shadow-2xl">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-lg font-bold text-foreground">{editingId ? t("editRecurring") : t("newRecurring")}</h2>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors"><X className="w-5 h-5" /></button>
                </div>
                <form onSubmit={onSubmit} className="space-y-5">
                    <div>
                        <label className="block text-xs text-muted-foreground mb-1.5 font-medium">{t("templateName")} *</label>
                        <input type="text" required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                            className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors"
                            placeholder={t("recurringNamePlaceholder")} />
                    </div>
                    <div className="grid grid-cols-3 gap-4">
                        <div>
                            <label className="block text-xs text-muted-foreground mb-1.5 font-medium">{t("client")} *</label>
                            <select required value={form.client_id} onChange={e => setForm(f => ({ ...f, client_id: e.target.value }))}
                                className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors">
                                <option value="">{t("recurringSelectClient")}</option>
                                {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="block text-xs text-muted-foreground mb-1.5 font-medium">{t("intervalType")}</label>
                            <select value={form.interval_type} onChange={e => setForm(f => ({ ...f, interval_type: e.target.value }))}
                                className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors">
                                <option value="weekly">{t("weekly")}</option>
                                <option value="monthly">{t("monthly")}</option>
                                <option value="quarterly">{t("quarterly")}</option>
                                <option value="yearly">{t("yearly")}</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-xs text-muted-foreground mb-1.5 font-medium">{t("recurringFirstIssue")} *</label>
                            <input type="date" required value={form.next_run_date} onChange={e => setForm(f => ({ ...f, next_run_date: e.target.value }))}
                                className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors" />
                        </div>
                    </div>

                    <div>
                        <div className="flex items-center justify-between mb-3">
                            <p className="text-sm font-semibold text-foreground">{t("recurringInvoiceLines")}</p>
                            <button type="button" onClick={addLine} className="text-xs text-primary hover:text-primary flex items-center gap-1 transition-colors">
                                <Plus className="w-3 h-3" /> {t("add")}
                            </button>
                        </div>
                        <div className="space-y-2">
                            {form.lines.map((line, i) => (
                                <div key={i} className="grid grid-cols-12 gap-2 items-center bg-muted rounded-xl p-3">
                                    <div className="col-span-5">
                                        <input type="text" placeholder={`${t("descriptionLabel")} *`} value={line.description} onChange={e => setLine(i, "description", e.target.value)}
                                            className="w-full bg-card border border-border text-foreground text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-primary" />
                                    </div>
                                    <div className="col-span-2">
                                        <input type="number" min={0.01} step={0.01} placeholder={t("quantity")} value={line.quantity} onChange={e => setLine(i, "quantity", parseFloat(e.target.value) || 0)}
                                            className="w-full bg-card border border-border text-foreground text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-primary" />
                                    </div>
                                    <div className="col-span-2">
                                        <input type="number" min={0} step={0.01} placeholder={t("unitPriceFull")} value={line.unit_price} onChange={e => setLine(i, "unit_price", parseFloat(e.target.value) || 0)}
                                            className="w-full bg-card border border-border text-foreground text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-primary" />
                                    </div>
                                    <div className="col-span-2">
                                        <select value={line.tax_percentage} onChange={e => setLine(i, "tax_percentage", parseFloat(e.target.value))}
                                            className="w-full bg-card border border-border text-foreground text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-primary">
                                            {[0, 4, 10, 21].map(v => <option key={v} value={v}>{v}%</option>)}
                                        </select>
                                    </div>
                                    <div className="col-span-1 flex justify-end">
                                        <button type="button" onClick={() => removeLine(i)} disabled={form.lines.length === 1}
                                            className="p-1.5 hover:bg-rose-500/10 rounded-lg text-muted-foreground hover:text-rose-400 transition-colors disabled:opacity-30">
                                            <X className="w-3.5 h-3.5" />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                        <div className="flex justify-between items-center mt-3 px-3">
                            <span className="text-xs text-muted-foreground">{t("recurringTotalPerIssue")}</span>
                            <span className="text-sm font-bold text-foreground font-mono">{fmt(totalAmount)}</span>
                        </div>
                    </div>

                    <div>
                        <label className="block text-xs text-muted-foreground mb-1.5 font-medium">{t("invoiceNotes")}</label>
                        <textarea value={form.notes} rows={2} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                            className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors resize-none"
                            placeholder={t("recurringNotesPlaceholder")} />
                    </div>

                    <div className="flex gap-3 pt-2">
                        <button type="button" onClick={onClose} className="flex-1 py-2.5 rounded-xl border border-border text-muted-foreground text-sm hover:bg-accent/50 transition-colors">{tc("cancel")}</button>
                        <button type="submit" disabled={saving} className="flex-1 py-2.5 rounded-xl bg-primary hover:bg-primary text-foreground text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2">
                            {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                            {editingId ? t("saveChanges") : t("createTemplate")}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
