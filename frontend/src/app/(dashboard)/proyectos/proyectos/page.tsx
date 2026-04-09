"use client";

import { useEffect, useState, useRef } from "react";
import { api, type Project } from "@/lib/api";
import { Plus, FolderGit2, CheckCircle2, Clock, PlayCircle, MoreHorizontal, Pencil, Trash2, X } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";

export default function ProyectosListado() {
    const toast = useToastStore();
    const [projects, setProjects] = useState<Project[]>([]);
    const [loading, setLoading] = useState(true);

    const [isCreateOpen, setCreateOpen] = useState(false);
    const [newProject, setNewProject] = useState<Partial<Project>>({ name: '', description: '', budget: 0, status: 'active' });

    const [editProject, setEditProject] = useState<Project | null>(null);
    const [editForm, setEditForm] = useState<Partial<Project>>({});

    const [openMenuId, setOpenMenuId] = useState<string | null>(null);
    const menuRef = useRef<HTMLDivElement>(null);

    const loadData = async () => {
        setLoading(true);
        try {
            setProjects(await api.projects.list());
        } catch (error) {
            logError("proyectos/proyectos/page", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { loadData(); }, []);

    // Cierra menú al hacer clic fuera
    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
                setOpenMenuId(null);
            }
        };
        document.addEventListener("mousedown", handler);
        return () => document.removeEventListener("mousedown", handler);
    }, []);

    const createProject = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await api.projects.create(newProject);
            setCreateOpen(false);
            setNewProject({ name: '', description: '', budget: 0, status: 'active' });
            loadData();
        } catch { toast.error("Error creando el proyecto"); }
    };

    const saveEdit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editProject) return;
        try {
            await api.projects.update(editProject.id, editForm);
            setEditProject(null);
            loadData();
        } catch { toast.error("Error actualizando el proyecto"); }
    };

    const deleteProject = async (project: Project) => {
        if (!await showConfirm({ message: `¿Eliminar el proyecto "${project.name}"? Se borrarán también sus tareas.`, confirmLabel: "Eliminar", confirmVariant: "danger" })) return;
        try {
            await api.projects.delete(project.id);
            loadData();
        } catch { toast.error("Error eliminando el proyecto"); }
    };

    const statusConfig: Record<string, { label: string; bg: string; text: string; icon: any }> = {
        active: { label: "Activo", bg: "bg-blue-500/10", text: "text-blue-400", icon: PlayCircle },
        completed: { label: "Completado", bg: "bg-emerald-500/10", text: "text-emerald-400", icon: CheckCircle2 },
        on_hold: { label: "En Pausa", bg: "bg-amber-500/10", text: "text-amber-400", icon: Clock },
    };

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-foreground mb-2">Proyectos</h1>
                    <p className="text-muted-foreground">Controla el presupuesto y el estado de tus proyectos en curso.</p>
                </div>
                <button onClick={() => setCreateOpen(true)} className="flex items-center justify-center gap-2 bg-primary hover:bg-primary text-foreground px-5 py-2.5 rounded-xl transition-all shadow-lg shadow-primary/20 font-medium">
                    <Plus className="w-5 h-5" />
                    Nuevo Proyecto
                </button>
            </div>

            {/* Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {loading ? (
                    <div className="col-span-full py-12 text-center text-muted-foreground">Cargando proyectos...</div>
                ) : projects.length === 0 ? (
                    <div className="col-span-full py-12 text-center bg-card border border-border rounded-2xl flex flex-col items-center">
                        <FolderGit2 className="w-12 h-12 text-muted-foreground mb-4" />
                        <h3 className="text-lg font-medium text-foreground mb-1">Sin Proyectos</h3>
                        <p className="text-sm text-muted-foreground">Pulsa &quot;Nuevo Proyecto&quot; para empezar.</p>
                    </div>
                ) : (
                    projects.map(project => {
                        const sConf = statusConfig[project.status] || statusConfig['active'];
                        const StatusIcon = sConf.icon;

                        return (
                            <div key={project.id} className="bg-card border border-border hover:border-primary/20 rounded-2xl p-6 flex flex-col transition-colors shadow-black/20 hover:shadow-xl relative group">
                                {/* Menú opciones */}
                                <div className="absolute top-4 right-4 z-10" ref={openMenuId === project.id ? menuRef : null}>
                                    <button
                                        onClick={(e) => { e.preventDefault(); setOpenMenuId(openMenuId === project.id ? null : project.id); }}
                                        className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent opacity-0 group-hover:opacity-100 transition-all"
                                    >
                                        <MoreHorizontal className="w-4 h-4" />
                                    </button>
                                    {openMenuId === project.id && (
                                        <div className="absolute right-0 top-8 w-40 bg-muted border border-border rounded-xl shadow-xl overflow-hidden z-20">
                                            <button
                                                onClick={() => { setEditProject(project); setEditForm({ name: project.name, description: project.description, budget: project.budget, status: project.status }); setOpenMenuId(null); }}
                                                className="flex items-center gap-2.5 w-full px-4 py-2.5 text-sm text-foreground hover:bg-accent/50 transition-colors"
                                            >
                                                <Pencil className="w-3.5 h-3.5 text-muted-foreground" /> Editar
                                            </button>
                                            <button
                                                onClick={() => { setOpenMenuId(null); deleteProject(project); }}
                                                className="flex items-center gap-2.5 w-full px-4 py-2.5 text-sm text-red-400 hover:bg-red-500/10 transition-colors"
                                            >
                                                <Trash2 className="w-3.5 h-3.5" /> Eliminar
                                            </button>
                                        </div>
                                    )}
                                </div>

                                {/* Contenido tarjeta (enlace) */}
                                <Link href={`/proyectos/tareas?project_id=${project.id}`} className="flex flex-col flex-1">
                                    <div className="flex items-start justify-between mb-4 pr-8">
                                        <div className="flex-1 min-w-0">
                                            <h3 className="text-lg font-semibold text-foreground truncate group-hover:text-primary transition-colors">
                                                {project.name}
                                            </h3>
                                            <p className="text-sm text-muted-foreground line-clamp-2 mt-1">
                                                {project.description || 'Sin descripción'}
                                            </p>
                                        </div>
                                        <div className={cn("px-2.5 py-1 rounded-full flex items-center gap-1.5 shrink-0 border border-transparent ml-2", sConf.bg, sConf.text)}>
                                            <StatusIcon className="w-3.5 h-3.5" />
                                            <span className="text-xs font-medium">{sConf.label}</span>
                                        </div>
                                    </div>
                                    <div className="mt-auto pt-4 border-t border-border flex items-center justify-between">
                                        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Presupuesto</span>
                                        <span className="text-sm font-bold text-foreground">
                                            {Number(project.budget).toLocaleString('es-ES')} €
                                        </span>
                                    </div>
                                </Link>
                            </div>
                        );
                    })
                )}
            </div>

            {/* Modal Crear */}
            {isCreateOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
                    <div className="bg-card border border-border rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
                        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                            <h3 className="text-lg font-semibold text-foreground">Crear Proyecto</h3>
                            <button onClick={() => setCreateOpen(false)} className="text-muted-foreground hover:text-foreground"><X className="w-5 h-5" /></button>
                        </div>
                        <form onSubmit={createProject} className="p-6 space-y-4">
                            <div>
                                <label className="block text-sm text-muted-foreground mb-1">Nombre del Proyecto</label>
                                <input required type="text" className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-foreground outline-none focus:border-primary"
                                    value={newProject.name} onChange={e => setNewProject({ ...newProject, name: e.target.value })} />
                            </div>
                            <div>
                                <label className="block text-sm text-muted-foreground mb-1">Presupuesto (€)</label>
                                <input required type="number" step="0.01" className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-foreground outline-none focus:border-primary"
                                    value={newProject.budget} onChange={e => setNewProject({ ...newProject, budget: Number(e.target.value) })} />
                            </div>
                            <div>
                                <label className="block text-sm text-muted-foreground mb-1">Descripción corta</label>
                                <textarea className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-foreground outline-none focus:border-primary resize-none h-24"
                                    value={newProject.description || ''} onChange={e => setNewProject({ ...newProject, description: e.target.value })} />
                            </div>
                            <div className="flex justify-end gap-3 pt-2 border-t border-border">
                                <button type="button" onClick={() => setCreateOpen(false)} className="px-4 py-2 text-muted-foreground hover:text-foreground">Cancelar</button>
                                <button type="submit" className="px-4 py-2 bg-primary hover:bg-primary text-foreground rounded-xl">Crear</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Modal Editar */}
            {editProject && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
                    <div className="bg-card border border-border rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
                        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                            <h3 className="text-lg font-semibold text-foreground">Editar Proyecto</h3>
                            <button onClick={() => setEditProject(null)} className="text-muted-foreground hover:text-foreground"><X className="w-5 h-5" /></button>
                        </div>
                        <form onSubmit={saveEdit} className="p-6 space-y-4">
                            <div>
                                <label className="block text-sm text-muted-foreground mb-1">Nombre</label>
                                <input required type="text" className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-foreground outline-none focus:border-primary"
                                    value={editForm.name || ''} onChange={e => setEditForm({ ...editForm, name: e.target.value })} />
                            </div>
                            <div>
                                <label className="block text-sm text-muted-foreground mb-1">Presupuesto (€)</label>
                                <input required type="number" step="0.01" className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-foreground outline-none focus:border-primary"
                                    value={editForm.budget ?? ''} onChange={e => setEditForm({ ...editForm, budget: Number(e.target.value) })} />
                            </div>
                            <div>
                                <label className="block text-sm text-muted-foreground mb-1">Estado</label>
                                <select className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-foreground outline-none focus:border-primary"
                                    value={editForm.status || 'active'} onChange={e => setEditForm({ ...editForm, status: e.target.value })}>
                                    <option value="active">Activo</option>
                                    <option value="on_hold">En Pausa</option>
                                    <option value="completed">Completado</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm text-muted-foreground mb-1">Descripción</label>
                                <textarea className="w-full bg-muted border border-border rounded-xl px-4 py-2 text-foreground outline-none focus:border-primary resize-none h-20"
                                    value={editForm.description || ''} onChange={e => setEditForm({ ...editForm, description: e.target.value })} />
                            </div>
                            <div className="flex justify-end gap-3 pt-2 border-t border-border">
                                <button type="button" onClick={() => setEditProject(null)} className="px-4 py-2 text-muted-foreground hover:text-foreground">Cancelar</button>
                                <button type="submit" className="px-4 py-2 bg-primary hover:bg-primary text-foreground rounded-xl">Guardar</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
