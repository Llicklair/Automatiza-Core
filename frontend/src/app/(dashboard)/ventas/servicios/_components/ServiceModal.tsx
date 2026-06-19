"use client";

import { HeartHandshake, X, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
import type { FormState } from "../_hooks/useServicios";

interface Props {
    editingId: string | null;
    form: FormState;
    setForm: React.Dispatch<React.SetStateAction<FormState>>;
    isSubmitting: boolean;
    onClose: () => void;
    onSubmit: (e: React.FormEvent) => void;
}

export function ServiceModal({ editingId, form, setForm, isSubmitting, onClose, onSubmit }: Props) {
    const t = useTranslations("ventas");
    const tc = useTranslations("common");

    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-card border border-border rounded-2xl w-full max-w-xl overflow-hidden shadow-2xl">
                <div className="p-5 border-b border-border flex justify-between items-center bg-muted">
                    <h2 className="text-lg font-medium text-foreground flex items-center gap-2">
                        <HeartHandshake className="w-4 h-4 text-purple-400" />
                        {editingId ? t("editService") : t("newService")}
                    </h2>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground" aria-label={t("closeServiceForm")}>
                        <X className="w-5 h-5" aria-hidden="true" />
                    </button>
                </div>
                <form onSubmit={onSubmit} className="p-6 space-y-5">
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("name")} *</label>
                            <input
                                type="text"
                                required
                                value={form.name}
                                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-purple-500"
                            />
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("serviceSkuRef")}</label>
                            <input
                                type="text"
                                value={form.sku}
                                onChange={e => setForm(f => ({ ...f, sku: e.target.value }))}
                                placeholder={t("serviceOptional")}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-purple-500 font-mono text-sm"
                            />
                        </div>
                    </div>
                    <div>
                        <label className="block text-sm text-muted-foreground mb-1.5">{t("descriptionLabel")}</label>
                        <textarea
                            value={form.description}
                            onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                            className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-purple-500 resize-none h-20"
                        />
                    </div>
                    <div className="grid grid-cols-2 gap-4 border-t border-border pt-4">
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("serviceBasePriceEur")} *</label>
                            <input
                                type="number"
                                required
                                min="0"
                                step="0.01"
                                value={form.price}
                                onChange={e => setForm(f => ({ ...f, price: e.target.value }))}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-purple-500"
                            />
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">{t("serviceVatPercent")}</label>
                            <select
                                value={form.tax_percentage}
                                onChange={e => setForm(f => ({ ...f, tax_percentage: e.target.value }))}
                                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-purple-500"
                            >
                                <option value="21">21%</option>
                                <option value="10">{t("serviceVatReduced")}</option>
                                <option value="4">{t("serviceVatSuperReduced")}</option>
                                <option value="0">{t("serviceVatExempt")}</option>
                            </select>
                        </div>
                    </div>
                    <div className="pt-4 flex justify-end gap-3">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-5 py-2.5 text-foreground hover:text-foreground transition-colors font-medium border border-border rounded-lg"
                        >
                            {tc("cancel")}
                        </button>
                        <button
                            type="submit"
                            disabled={isSubmitting || !form.name || !form.price}
                            className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-foreground px-6 py-2.5 rounded-lg font-medium transition-colors shadow-lg shadow-purple-500/20 disabled:opacity-50"
                        >
                            {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                            {editingId ? tc("save") : t("createService")}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
