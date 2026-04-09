"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { api, ProjectTask } from "@/lib/api";
import {
    KanbanSquare, Plus, Search, MoreHorizontal,
    Calendar, CheckCircle2, Clock, PlayCircle, X, Loader2,
    Pencil, Trash2
} from "lucide-react";
import { format } from "date-fns";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";

type TaskStatus = 'todo' | 'in_progress' | 'done';

function TasksKanbanContent() {
    const toast = useToastStore();
    const searchParams = useSearchParams();
    const projectId = searchParams.get("project_id");

    const [tasks, setTasks] = useState<ProjectTask[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [draggedTask, setDraggedTask] = useState<ProjectTask | null>(null);

    // Modal crear
    const [showModal, setShowModal] = useState(false);
    const [saving, setSaving] = useState(false);
    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const [dueDate, setDueDate] = useState("");

    // Modal editar
    const [editTask, setEditTask] = useState<ProjectTask | null>(null);
    const [editTitle, setEditTitle] = useState("");
    const [editDescription, setEditDescription] = useState("");
    const [editDueDate, setEditDueDate] = useState("");
    const [editSaving, setEditSaving] = useState(false);

    // Menú contextual
    const [openMenuId, setOpenMenuId] = useState<string | null>(null);

    // eslint-disable-next-line react-hooks/exhaustive-deps
    useEffect(() => { loadData(); }, [projectId]);

    // Cierra menú al hacer clic fuera
    useEffect(() => {
        const handler = () => setOpenMenuId(null);
        document.addEventListener("click", handler);
        return () => document.removeEventListener("click", handler);
    }, []);

    const loadData = async () => {
        setIsLoading(true);
        try {
            const data = await api.projects.tasks.list(projectId ? { project_id: projectId } : undefined);
            setTasks(data);
        } catch (error) {
            logError("proyectos/tareas/page", error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!title.trim()) return;
        setSaving(true);
        try {
            await api.projects.tasks.create({
                title,
                description: description || undefined,
                due_date: dueDate ? new Date(dueDate).toISOString() : undefined,
                status: "todo",
                ...(projectId ? { project_id: projectId } : {}),
            });
            setShowModal(false);
            setTitle(""); setDescription(""); setDueDate("");
            await loadData();
        } catch (error) {
            logError("proyectos/tareas/page", error);
            toast.error("Error al crear tarea");
        } finally {
            setSaving(false);
        }
    };

    const handleEditOpen = (task: ProjectTask) => {
        setEditTask(task);
        setEditTitle(task.title);
        setEditDescription(task.description || "");
        setEditDueDate(task.due_date ? task.due_date.slice(0, 10) : "");
        setOpenMenuId(null);
    };

    const handleEditSave = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editTask) return;
        setEditSaving(true);
        try {
            await api.projects.tasks.update(editTask.id, {
                title: editTitle,
                description: editDescription || undefined,
                due_date: editDueDate ? new Date(editDueDate).toISOString() : undefined,
            });
            setEditTask(null);
            await loadData();
        } catch {
            toast.error("Error al guardar tarea");
        } finally {
            setEditSaving(false);
        }
    };

    const handleDelete = async (task: ProjectTask) => {
        setOpenMenuId(null);
        if (!await showConfirm({ message: `¿Eliminar la tarea "${task.title}"?`, confirmLabel: "Eliminar", confirmVariant: "danger" })) return;
        try {
            await api.projects.tasks.delete(task.id);
            setTasks(prev => prev.filter(t => t.id !== task.id));
        } catch {
            toast.error("Error al eliminar tarea");
        }
    };

    const handleDragStart = (e: React.DragEvent, task: ProjectTask) => {
        setDraggedTask(task);
        e.dataTransfer.setData('taskId', task.id);
        e.dataTransfer.effectAllowed = 'move';
        setTimeout(() => {
            if (e.target instanceof HTMLElement) e.target.style.opacity = '0.5';
        }, 0);
    };

    const handleDragEnd = (e: React.DragEvent) => {
        setDraggedTask(null);
        if (e.target instanceof HTMLElement) e.target.style.opacity = '1';
    };

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
    };

    const handleDrop = async (e: React.DragEvent, newStatus: TaskStatus) => {
        e.preventDefault();
        if (!draggedTask || draggedTask.status === newStatus) return;
        setTasks(tasks.map(t => t.id === draggedTask.id ? { ...t, status: newStatus } : t));
        try {
            await api.projects.tasks.update(draggedTask.id, { status: newStatus });
        } catch {
            loadData();
        }
    };

    const getTasksByStatus = (status: TaskStatus) => tasks.filter(t => t.status === status);

    const renderColumn = (colTitle: string, status: TaskStatus) => {
        const columnTasks = getTasksByStatus(status);
        let headerColor = "bg-muted text-foreground";
        if (status === 'in_progress') headerColor = "bg-blue-500/10 text-blue-400 border-blue-500/20";
        if (status === 'done') headerColor = "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";

        return (
            <div
                className="flex flex-col bg-card border border-border rounded-xl h-[70vh] min-w-[320px] max-w-sm flex-1 overflow-hidden transition-colors"
                onDragOver={handleDragOver}
                onDrop={(e) => handleDrop(e, status)}
            >
                <div className={`px-4 py-3 border-b border-border font-medium text-sm flex items-center justify-between ${headerColor} border`}>
                    <div className="flex items-center gap-2">
                        {status === 'todo' && <Clock className="w-4 h-4" />}
                        {status === 'in_progress' && <PlayCircle className="w-4 h-4" />}
                        {status === 'done' && <CheckCircle2 className="w-4 h-4" />}
                        {colTitle}
                    </div>
                    <span className="bg-muted/50 text-xs px-2 py-0.5 rounded-full">{columnTasks.length}</span>
                </div>

                <div className="flex-1 p-3 overflow-y-auto custom-scrollbar space-y-3">
                    {columnTasks.map(task => (
                        <div
                            key={task.id}
                            draggable
                            onDragStart={(e) => handleDragStart(e, task)}
                            onDragEnd={handleDragEnd}
                            className="bg-muted border border-border p-3.5 rounded-xl cursor-grab shadow-sm shadow-black/20 hover:border-border hover:bg-muted transition-all group"
                        >
                            <div className="flex justify-between items-start mb-2">
                                <span className="text-[10px] font-mono text-muted-foreground uppercase px-1.5 py-0.5 bg-muted rounded">
                                    {task.id.slice(0, 6)}
                                </span>
                                {/* Menú MoreHorizontal */}
                                <div className="relative" onClick={e => e.stopPropagation()}>
                                    <button
                                        onClick={() => setOpenMenuId(openMenuId === task.id ? null : task.id)}
                                        className="text-muted-foreground hover:text-foreground opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded hover:bg-accent"
                                    >
                                        <MoreHorizontal className="w-4 h-4" />
                                    </button>
                                    {openMenuId === task.id && (
                                        <div className="absolute right-0 top-6 w-36 bg-muted border border-border rounded-xl shadow-xl overflow-hidden z-20">
                                            <button
                                                onClick={() => handleEditOpen(task)}
                                                className="flex items-center gap-2 w-full px-3 py-2 text-xs text-foreground hover:bg-accent/50 transition-colors"
                                            >
                                                <Pencil className="w-3 h-3 text-muted-foreground" /> Editar
                                            </button>
                                            <button
                                                onClick={() => handleDelete(task)}
                                                className="flex items-center gap-2 w-full px-3 py-2 text-xs text-red-400 hover:bg-red-500/10 transition-colors"
                                            >
                                                <Trash2 className="w-3 h-3" /> Eliminar
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </div>

                            <h4 className="text-sm font-medium text-foreground mb-1 leading-snug">{task.title}</h4>

                            {task.description && (
                                <p className="text-xs text-muted-foreground line-clamp-2 mb-3 leading-relaxed">
                                    {task.description}
                                </p>
                            )}

                            <div className="flex items-center justify-between mt-3 pt-3 border-t border-border">
                                <div className="flex -space-x-1.5">
                                    <div className="w-6 h-6 rounded-full bg-primary/20 border border-border flex items-center justify-center text-[10px] text-primary font-bold" title="IA">
                                        IA
                                    </div>
                                    {task.assignee_id && (
                                        <div className="w-6 h-6 rounded-full bg-accent border border-border flex items-center justify-center text-[10px] text-foreground font-bold" title="Humano">
                                            HM
                                        </div>
                                    )}
                                </div>
                                {task.due_date && (
                                    <div className="flex items-center gap-1 text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                                        <Calendar className="w-3 h-3" />
                                        {format(new Date(task.due_date), "MMM d")}
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                    {columnTasks.length === 0 && (
                        <div className="h-full w-full border-2 border-dashed border-border rounded-xl flex items-center justify-center text-muted-foreground text-xs font-medium">
                            Arrastra tareas aquí
                        </div>
                    )}
                </div>
            </div>
        );
    };

    return (
        <div className="min-h-screen bg-background text-foreground p-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
                <div>
                    <h1 className="text-3xl font-light text-foreground flex items-center gap-3">
                        <div className="p-2 bg-pink-500/10 rounded-xl">
                            <KanbanSquare className="w-8 h-8 text-pink-400" />
                        </div>
                        Pizarra de Tareas
                    </h1>
                    <p className="text-muted-foreground mt-2 ml-14 text-sm max-w-2xl">
                        Tablero Kanban para el equipo. La IA descompondrá las transcripciones de las reuniones en tareas medibles y las asignará aquí automáticamente.
                    </p>
                </div>

                <div className="flex gap-3">
                    <button className="flex items-center gap-2 bg-card border border-border hover:border-border hover:bg-muted text-foreground px-5 py-2.5 rounded-full font-medium transition-colors">
                        <Search className="w-4 h-4" />
                        Filtrar
                    </button>
                    <button
                        onClick={() => setShowModal(true)}
                        className="flex items-center gap-2 bg-pink-600 hover:bg-pink-500 text-foreground shadow-lg shadow-pink-500/20 px-5 py-2.5 rounded-full font-medium transition-colors"
                    >
                        <Plus className="w-4 h-4" />
                        Añadir Tarea
                    </button>
                </div>
            </div>

            {isLoading ? (
                <div className="flex justify-center p-20">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pink-500"></div>
                </div>
            ) : (
                <div className="flex gap-6 overflow-x-auto pb-6 custom-scrollbar px-1">
                    {renderColumn("Por Hacer", "todo")}
                    {renderColumn("En Curso", "in_progress")}
                    {renderColumn("Completadas", "done")}
                </div>
            )}

            {/* Modal Nueva Tarea */}
            {showModal && (
                <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={() => setShowModal(false)}>
                    <div className="w-full max-w-md rounded-2xl border border-border bg-card overflow-hidden" onClick={e => e.stopPropagation()}>
                        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-muted">
                            <h2 className="font-medium text-foreground flex items-center gap-2">
                                <Plus className="w-4 h-4 text-pink-400" />
                                Nueva Tarea
                            </h2>
                            <button onClick={() => setShowModal(false)} className="text-muted-foreground hover:text-foreground"><X className="w-5 h-5" /></button>
                        </div>
                        <form onSubmit={handleCreate} className="p-6 space-y-4">
                            <div>
                                <label className="text-sm text-muted-foreground block mb-1.5 font-medium">Título *</label>
                                <input required value={title} onChange={e => setTitle(e.target.value)}
                                    placeholder="Ej: Revisar contrato"
                                    className="w-full px-4 py-2.5 rounded-xl bg-background border border-border text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:border-pink-500 transition-colors" />
                            </div>
                            <div>
                                <label className="text-sm text-muted-foreground block mb-1.5">Descripción</label>
                                <textarea rows={2} value={description} onChange={e => setDescription(e.target.value)}
                                    placeholder="Detalles..."
                                    className="w-full px-4 py-2.5 rounded-xl bg-background border border-border text-foreground text-sm placeholder:text-muted-foreground resize-none focus:outline-none focus:border-pink-500 transition-colors" />
                            </div>
                            <div>
                                <label className="text-sm text-muted-foreground block mb-1.5">Fecha límite (opcional)</label>
                                <input type="date" value={dueDate} onChange={e => setDueDate(e.target.value)}
                                    className="w-full px-4 py-2.5 rounded-xl bg-background border border-border text-foreground text-sm focus:outline-none focus:border-pink-500 transition-colors [color-scheme:dark]" />
                            </div>
                            <div className="flex gap-3 pt-4">
                                <button type="button" onClick={() => setShowModal(false)}
                                    className="flex-1 py-2.5 rounded-xl text-muted-foreground font-medium text-sm hover:text-foreground hover:bg-accent/50 transition border border-transparent hover:border-border">
                                    Cancelar
                                </button>
                                <button type="submit" disabled={saving || !title.trim()}
                                    className="flex-1 py-2.5 rounded-xl bg-pink-600 hover:bg-pink-500 disabled:opacity-50 text-foreground text-sm font-medium transition shadow-lg shadow-pink-500/20 flex items-center justify-center gap-2">
                                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : "Añadir al Tablero"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Modal Editar Tarea */}
            {editTask && (
                <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={() => setEditTask(null)}>
                    <div className="w-full max-w-md rounded-2xl border border-border bg-card overflow-hidden" onClick={e => e.stopPropagation()}>
                        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-muted">
                            <h2 className="font-medium text-foreground flex items-center gap-2">
                                <Pencil className="w-4 h-4 text-muted-foreground" />
                                Editar Tarea
                            </h2>
                            <button onClick={() => setEditTask(null)} className="text-muted-foreground hover:text-foreground"><X className="w-5 h-5" /></button>
                        </div>
                        <form onSubmit={handleEditSave} className="p-6 space-y-4">
                            <div>
                                <label className="text-sm text-muted-foreground block mb-1.5 font-medium">Título *</label>
                                <input required value={editTitle} onChange={e => setEditTitle(e.target.value)}
                                    className="w-full px-4 py-2.5 rounded-xl bg-background border border-border text-foreground text-sm focus:outline-none focus:border-pink-500 transition-colors" />
                            </div>
                            <div>
                                <label className="text-sm text-muted-foreground block mb-1.5">Descripción</label>
                                <textarea rows={2} value={editDescription} onChange={e => setEditDescription(e.target.value)}
                                    className="w-full px-4 py-2.5 rounded-xl bg-background border border-border text-foreground text-sm resize-none focus:outline-none focus:border-pink-500 transition-colors" />
                            </div>
                            <div>
                                <label className="text-sm text-muted-foreground block mb-1.5">Fecha límite</label>
                                <input type="date" value={editDueDate} onChange={e => setEditDueDate(e.target.value)}
                                    className="w-full px-4 py-2.5 rounded-xl bg-background border border-border text-foreground text-sm focus:outline-none focus:border-pink-500 transition-colors [color-scheme:dark]" />
                            </div>
                            <div className="flex gap-3 pt-4">
                                <button type="button" onClick={() => setEditTask(null)}
                                    className="flex-1 py-2.5 rounded-xl text-muted-foreground font-medium text-sm hover:text-foreground hover:bg-accent/50 transition border border-transparent hover:border-border">
                                    Cancelar
                                </button>
                                <button type="submit" disabled={editSaving || !editTitle.trim()}
                                    className="flex-1 py-2.5 rounded-xl bg-pink-600 hover:bg-pink-500 disabled:opacity-50 text-foreground text-sm font-medium transition shadow-lg shadow-pink-500/20 flex items-center justify-center gap-2">
                                    {editSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : "Guardar Cambios"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

export default function TasksKanbanPage() {
    return (
        <Suspense fallback={<div className="min-h-screen bg-background flex items-center justify-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pink-500"></div></div>}>
            <TasksKanbanContent />
        </Suspense>
    );
}
