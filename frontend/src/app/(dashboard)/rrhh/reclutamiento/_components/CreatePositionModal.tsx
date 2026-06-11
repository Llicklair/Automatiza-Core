"use client";

import { useTranslations } from "next-intl";
import { X } from "lucide-react";

interface CreatePositionModalProps {
    form: { title: string; department: string; description: string; required_skills: string; experience_min_years: number };
    setForm: React.Dispatch<React.SetStateAction<CreatePositionModalProps["form"]>>;
    onClose: () => void;
    onCreate: () => void;
}

export function CreatePositionModal({ form, setForm, onClose, onCreate }: CreatePositionModalProps) {
    const t = useTranslations("rrhh");
    const tc = useTranslations("common");
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
            <div className="bg-card border border-border rounded-2xl p-6 w-full max-w-md space-y-4">
                <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-foreground">{t("reclutamiento.newPosition")}</h3>
                    <button onClick={onClose} aria-label={t("reclutamiento.positionModal.closeAria")}><X className="w-4 h-4 text-muted-foreground" aria-hidden="true" /></button>
                </div>
                <div className="space-y-3">
                    <input
                        placeholder={t("reclutamiento.positionModal.titlePlaceholder")}
                        value={form.title}
                        onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                        className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-violet-500/50"
                    />
                    <input
                        placeholder={t("reclutamiento.positionModal.departmentPlaceholder")}
                        value={form.department}
                        onChange={e => setForm(f => ({ ...f, department: e.target.value }))}
                        className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-violet-500/50"
                    />
                    <textarea
                        placeholder={t("reclutamiento.positionModal.descriptionPlaceholder")}
                        value={form.description}
                        onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                        rows={3}
                        className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-violet-500/50 resize-none"
                    />
                    <input
                        placeholder={t("reclutamiento.positionModal.skillsPlaceholder")}
                        value={form.required_skills}
                        onChange={e => setForm(f => ({ ...f, required_skills: e.target.value }))}
                        className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-violet-500/50"
                    />
                    <div className="flex items-center gap-2">
                        <label className="text-xs text-muted-foreground whitespace-nowrap">{t("reclutamiento.positionModal.minExperience")}</label>
                        <input
                            type="number"
                            min={0}
                            step={0.5}
                            value={form.experience_min_years}
                            onChange={e => setForm(f => ({ ...f, experience_min_years: parseFloat(e.target.value) || 0 }))}
                            className="w-20 bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-violet-500/50"
                        />
                    </div>
                </div>
                <div className="flex justify-end gap-2 pt-2">
                    <button
                        onClick={onClose}
                        className="px-3 py-1.5 rounded-lg text-xs text-muted-foreground hover:text-foreground transition-colors"
                    >
                        {tc("cancel")}
                    </button>
                    <button
                        onClick={onCreate}
                        disabled={!form.title.trim()}
                        className="px-4 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-foreground text-xs font-medium transition-colors"
                    >
                        {t("reclutamiento.positionModal.create")}
                    </button>
                </div>
            </div>
        </div>
    );
}
