"use client";

import { X } from "lucide-react";
import { type Project } from "@/lib/api";

interface Props {
    newProject: Partial<Project>;
    onChange: (p: Partial<Project>) => void;
    onSubmit: (e: React.FormEvent) => void;
    onClose: () => void;
}

export function CreateProjectModal({ newProject, onChange, onSubmit, onClose }: Props) {
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-card border border-border rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
                <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                    <h3 className="text-lg font-semibold text-foreground">Crear Proyecto</h3>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground" aria-label="Cerrar"><X className="w-5 h-5" aria-hidden="true" /></button>
                </div>
                <form onSubmit={onSubmit} className="p-6 space-y-4">
                    <div>
                        <label className="block text-sm text-muted-foreground mb-1">Nombre del Proyecto</label>
                        <input required type="text" className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-foreground outline-none focus:border-primary"
                            value={newProject.name} onChange={e => onChange({ ...newProject, name: e.target.value })} />
                    </div>
                    <div>
                        <label className="block text-sm text-muted-foreground mb-1">Presupuesto (€)</label>
                        <input required type="number" step="0.01" className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-foreground outline-none focus:border-primary"
                            value={newProject.budget} onChange={e => onChange({ ...newProject, budget: Number(e.target.value) })} />
                    </div>
                    <div>
                        <label className="block text-sm text-muted-foreground mb-1">Descripción corta</label>
                        <textarea className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-foreground outline-none focus:border-primary resize-none h-24"
                            value={newProject.description || ''} onChange={e => onChange({ ...newProject, description: e.target.value })} />
                    </div>
                    <div className="flex justify-end gap-3 pt-2 border-t border-border">
                        <button type="button" onClick={onClose} className="px-4 py-2 text-muted-foreground hover:text-foreground">Cancelar</button>
                        <button type="submit" className="px-4 py-2 bg-primary hover:bg-primary text-foreground rounded-xl">Crear</button>
                    </div>
                </form>
            </div>
        </div>
    );
}
