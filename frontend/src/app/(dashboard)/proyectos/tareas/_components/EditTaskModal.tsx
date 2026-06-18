"use client";

import { ProjectTask } from "@/lib/api";
import { Pencil, X, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";

interface EditTaskModalProps {
    editTask: ProjectTask;
    editTitle: string;
    setEditTitle: (v: string) => void;
    editDescription: string;
    setEditDescription: (v: string) => void;
    editDueDate: string;
    setEditDueDate: (v: string) => void;
    editSaving: boolean;
    onClose: () => void;
    onSubmit: (e: React.FormEvent) => void;
}

export function EditTaskModal({
    editTask, editTitle, setEditTitle, editDescription, setEditDescription,
    editDueDate, setEditDueDate, editSaving, onClose, onSubmit,
}: EditTaskModalProps) {
    const t = useTranslations("proyectos");
    const tc = useTranslations("common");
    return (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={onClose}>
            <div className="w-full max-w-md rounded-2xl border border-border bg-card overflow-hidden" onClick={e => e.stopPropagation()}>
                <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-muted">
                    <h2 className="font-medium text-foreground flex items-center gap-2">
                        <Pencil className="w-4 h-4 text-muted-foreground" />
                        {t("editTaskModal.title")}
                    </h2>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground" aria-label={tc("close")}><X className="w-5 h-5" aria-hidden="true" /></button>
                </div>
                <form onSubmit={onSubmit} className="p-6 space-y-4">
                    <div>
                        <label className="text-sm text-muted-foreground block mb-1.5 font-medium">{t("editTaskModal.titleLabel")}</label>
                        <input required value={editTitle} onChange={e => setEditTitle(e.target.value)}
                            className="w-full px-4 py-2.5 rounded-xl bg-background border border-border text-foreground text-sm focus:outline-none focus:border-pink-500 transition-colors" />
                    </div>
                    <div>
                        <label className="text-sm text-muted-foreground block mb-1.5">{t("editTaskModal.descriptionLabel")}</label>
                        <textarea rows={2} value={editDescription} onChange={e => setEditDescription(e.target.value)}
                            className="w-full px-4 py-2.5 rounded-xl bg-background border border-border text-foreground text-sm resize-none focus:outline-none focus:border-pink-500 transition-colors" />
                    </div>
                    <div>
                        <label className="text-sm text-muted-foreground block mb-1.5">{t("editTaskModal.dueDateLabel")}</label>
                        <input type="date" value={editDueDate} onChange={e => setEditDueDate(e.target.value)}
                            className="w-full px-4 py-2.5 rounded-xl bg-background border border-border text-foreground text-sm focus:outline-none focus:border-pink-500 transition-colors [color-scheme:dark]" />
                    </div>
                    <div className="flex gap-3 pt-4">
                        <button type="button" onClick={onClose}
                            className="flex-1 py-2.5 rounded-xl text-muted-foreground font-medium text-sm hover:text-foreground hover:bg-accent/50 transition border border-transparent hover:border-border">
                            {tc("cancel")}
                        </button>
                        <button type="submit" disabled={editSaving || !editTitle.trim()}
                            className="flex-1 py-2.5 rounded-xl bg-pink-600 hover:bg-pink-500 disabled:opacity-50 text-foreground text-sm font-medium transition shadow-lg shadow-pink-500/20 flex items-center justify-center gap-2">
                            {editSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : t("editTaskModal.save")}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
