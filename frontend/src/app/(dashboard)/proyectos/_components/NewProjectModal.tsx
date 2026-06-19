"use client";

import { X, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";

interface FormState {
    name: string;
    description: string;
    budget: string;
    start_date: string;
    due_date: string;
    status: string;
}

interface Props {
    form: FormState;
    onChange: (f: FormState) => void;
    onSubmit: (e: React.FormEvent) => void;
    onClose: () => void;
    saving: boolean;
    error: string;
}

export function NewProjectModal({ form, onChange, onSubmit, onClose, saving, error }: Props) {
    const t = useTranslations("proyectos");
    const tc = useTranslations("common");
    return (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" onClick={onClose}>
            <div className="w-full max-w-md rounded-2xl border border-border bg-card overflow-hidden" onClick={e => e.stopPropagation()}>
                <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                    <h2 className="font-semibold text-foreground">{t("newProjectModal.title")}</h2>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground" aria-label={tc("close")}><X className="w-5 h-5" aria-hidden="true" /></button>
                </div>
                <form onSubmit={onSubmit} className="p-6 space-y-4">
                    <div>
                        <label className="text-sm text-foreground block mb-1.5 font-medium">{t("newProjectModal.nameLabel")}</label>
                        <input required value={form.name} onChange={e => onChange({ ...form, name: e.target.value })}
                            placeholder={t("newProjectModal.namePlaceholder")}
                            className="w-full px-3 py-2.5 rounded-lg bg-card border border-border text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-purple-500" />
                    </div>
                    <div>
                        <label className="text-sm text-foreground block mb-1.5">{t("newProjectModal.descriptionLabel")}</label>
                        <textarea rows={2} value={form.description} onChange={e => onChange({ ...form, description: e.target.value })}
                            placeholder={t("newProjectModal.descriptionPlaceholder")}
                            className="w-full px-3 py-2.5 rounded-lg bg-card border border-border text-foreground text-sm placeholder:text-muted-foreground resize-none focus:outline-none focus:ring-2 focus:ring-purple-500" />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="text-sm text-foreground block mb-1.5">{t("newProjectModal.startDateLabel")}</label>
                            <input type="date" value={form.start_date} onChange={e => onChange({ ...form, start_date: e.target.value })}
                                className="w-full px-3 py-2.5 rounded-lg bg-card border border-border text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-purple-500" />
                        </div>
                        <div>
                            <label className="text-sm text-foreground block mb-1.5">{t("newProjectModal.dueDateLabel")}</label>
                            <input type="date" value={form.due_date} onChange={e => onChange({ ...form, due_date: e.target.value })}
                                className="w-full px-3 py-2.5 rounded-lg bg-card border border-border text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-purple-500" />
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="text-sm text-foreground block mb-1.5">{t("newProjectModal.budgetLabel")}</label>
                            <input type="number" value={form.budget} onChange={e => onChange({ ...form, budget: e.target.value })}
                                placeholder="5000"
                                className="w-full px-3 py-2.5 rounded-lg bg-card border border-border text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-purple-500" />
                        </div>
                        <div>
                            <label className="text-sm text-foreground block mb-1.5">{t("newProjectModal.statusLabel")}</label>
                            <select value={form.status} onChange={e => onChange({ ...form, status: e.target.value })}
                                className="w-full px-3 py-2.5 rounded-lg bg-card border border-border text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-purple-500">
                                <option value="active">{t("newProjectModal.statusActive")}</option>
                                <option value="on_hold">{t("newProjectModal.statusOnHold")}</option>
                                <option value="completed">{t("newProjectModal.statusCompleted")}</option>
                            </select>
                        </div>
                    </div>
                    {error && <p className="text-sm text-red-400 bg-red-500/10 p-3 rounded-lg">{error}</p>}
                    <div className="flex gap-3 pt-2">
                        <button type="button" onClick={onClose}
                            className="flex-1 py-2.5 rounded-xl border border-border text-muted-foreground text-sm hover:text-foreground transition">{tc("cancel")}</button>
                        <button type="submit" disabled={saving}
                            className="flex-1 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-foreground text-sm font-medium transition flex items-center justify-center gap-2">
                            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                            {saving ? t("newProjectModal.creating") : t("newProjectModal.submit")}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
