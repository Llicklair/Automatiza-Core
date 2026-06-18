"use client";

import { useTranslations } from "next-intl";

import { type Project, type ProjectTask } from "@/lib/api";

interface Props {
    newTask: Partial<ProjectTask>;
    projects: Project[];
    onChange: (t: Partial<ProjectTask>) => void;
    onSubmit: (e: React.FormEvent) => void;
    onClose: () => void;
}

export function NewTaskModal({ newTask, projects, onChange, onSubmit, onClose }: Props) {
    const t = useTranslations("proyectos");
    const tc = useTranslations("common");
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-card border border-border rounded-2xl w-full max-w-md shadow-2xl overflow-hidden p-6">
                <h3 className="text-lg font-semibold text-foreground mb-4">{t("newTaskModal.title")}</h3>

                {projects.length === 0 ? (
                    <div className="py-8 text-center bg-accent/50 rounded-xl border border-border">
                        <p className="text-sm text-muted-foreground mb-4 px-6">{t("newTaskModal.noProjects")}</p>
                        <button onClick={onClose} className="text-sm text-foreground bg-accent hover:bg-white/20 px-4 py-2 rounded-lg">{tc("close")}</button>
                    </div>
                ) : (
                    <form onSubmit={onSubmit} className="space-y-4">
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1">{t("newTaskModal.fieldTitle")}</label>
                            <input required type="text" className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-foreground outline-none focus:border-primary"
                                value={newTask.title} onChange={e => onChange({ ...newTask, title: e.target.value })} />
                        </div>

                        <div>
                            <label className="block text-sm text-muted-foreground mb-1">{t("newTaskModal.fieldProject")}</label>
                            <select required className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-foreground outline-none focus:border-primary"
                                value={newTask.project_id} onChange={e => onChange({ ...newTask, project_id: e.target.value })}>
                                {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm text-muted-foreground mb-1">{t("newTaskModal.fieldDescription")}</label>
                            <textarea className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-foreground outline-none focus:border-primary h-20 resize-none"
                                value={newTask.description || ''} onChange={e => onChange({ ...newTask, description: e.target.value })} />
                        </div>

                        <div className="flex justify-end gap-3 pt-4 border-t border-border">
                            <button type="button" onClick={onClose} className="px-4 py-2 text-muted-foreground hover:text-foreground">{tc("cancel")}</button>
                            <button type="submit" className="px-4 py-2 bg-primary hover:bg-primary text-foreground rounded-xl shadow-lg shadow-primary/20">{t("newTaskModal.submit")}</button>
                        </div>
                    </form>
                )}
            </div>
        </div>
    );
}
