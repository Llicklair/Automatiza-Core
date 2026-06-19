"use client";

import { X } from "lucide-react";
import { useTranslations } from "next-intl";
import { type Project } from "@/lib/api";

interface Props {
    editForm: Partial<Project>;
    onChange: (f: Partial<Project>) => void;
    onSubmit: (e: React.FormEvent) => void;
    onClose: () => void;
}

export function EditProjectModal({ editForm, onChange, onSubmit, onClose }: Props) {
    const t = useTranslations("proyectos");
    const tc = useTranslations("common");
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-card border border-border rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
                <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                    <h3 className="text-lg font-semibold text-foreground">{t("editModal.title")}</h3>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground" aria-label={tc("close")}><X className="w-5 h-5" aria-hidden="true" /></button>
                </div>
                <form onSubmit={onSubmit} className="p-6 space-y-4">
                    <div>
                        <label className="block text-sm text-muted-foreground mb-1">{t("editModal.nameLabel")}</label>
                        <input required type="text" className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-foreground outline-none focus:border-primary"
                            value={editForm.name || ''} onChange={e => onChange({ ...editForm, name: e.target.value })} />
                    </div>
                    <div>
                        <label className="block text-sm text-muted-foreground mb-1">{t("editModal.budgetLabel")}</label>
                        <input required type="number" step="0.01" className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-foreground outline-none focus:border-primary"
                            value={editForm.budget ?? ''} onChange={e => onChange({ ...editForm, budget: Number(e.target.value) })} />
                    </div>
                    <div>
                        <label className="block text-sm text-muted-foreground mb-1">{t("editModal.statusLabel")}</label>
                        <select className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-foreground outline-none focus:border-primary"
                            value={editForm.status || 'active'} onChange={e => onChange({ ...editForm, status: e.target.value })}>
                            <option value="active">{t("editModal.statusActive")}</option>
                            <option value="on_hold">{t("editModal.statusOnHold")}</option>
                            <option value="completed">{t("editModal.statusCompleted")}</option>
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm text-muted-foreground mb-1">{t("editModal.descriptionLabel")}</label>
                        <textarea className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-foreground outline-none focus:border-primary resize-none h-20"
                            value={editForm.description || ''} onChange={e => onChange({ ...editForm, description: e.target.value })} />
                    </div>
                    <div className="flex justify-end gap-3 pt-2 border-t border-border">
                        <button type="button" onClick={onClose} className="px-4 py-2 text-muted-foreground hover:text-foreground">{tc("cancel")}</button>
                        <button type="submit" className="px-4 py-2 bg-primary hover:bg-primary text-foreground rounded-xl">{tc("save")}</button>
                    </div>
                </form>
            </div>
        </div>
    );
}
