"use client";

import { Plus, FolderGit2, MoreHorizontal, Pencil, Trash2 } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { useProyectosListado, statusConfig } from "./_hooks/useProyectosListado";
import { CreateProjectModal } from "./_components/CreateProjectModal";
import { EditProjectModal } from "./_components/EditProjectModal";

export default function ProyectosListado() {
    const {
        projects, loading,
        isCreateOpen, setCreateOpen,
        newProject, setNewProject,
        editProject, setEditProject,
        editForm, setEditForm,
        openMenuId, setOpenMenuId,
        menuRef,
        createProject, saveEdit, deleteProject, openEditModal,
    } = useProyectosListado();

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
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
                                                onClick={() => openEditModal(project)}
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

            {isCreateOpen && (
                <CreateProjectModal
                    newProject={newProject}
                    onChange={setNewProject}
                    onSubmit={createProject}
                    onClose={() => setCreateOpen(false)}
                />
            )}

            {editProject && (
                <EditProjectModal
                    editForm={editForm}
                    onChange={setEditForm}
                    onSubmit={saveEdit}
                    onClose={() => setEditProject(null)}
                />
            )}
        </div>
    );
}
