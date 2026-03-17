"use client";

import { useEffect, useState, useCallback } from "react";
import { api, type Project, type ProjectTask } from "@/lib/api";
import { Plus, Clock, ArrowRight, FolderGit2, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";

const STAGES = [
    { id: 'todo', label: 'Por Hacer', color: 'border-zinc-500/30 bg-zinc-500/5', dot: 'bg-zinc-400' },
    { id: 'in_progress', label: 'En Curso', color: 'border-blue-500/30 bg-blue-500/5', dot: 'bg-blue-400' },
    { id: 'done', label: 'Completado', color: 'border-emerald-500/30 bg-emerald-500/5', dot: 'bg-emerald-400' },
];

export default function ProjectTasksPage() {
    const toast = useToastStore();
    const [tasks, setTasks] = useState<ProjectTask[]>([]);
    const [projects, setProjects] = useState<Project[]>([]);
    const [loading, setLoading] = useState(true);

    const [isModalOpen, setModalOpen] = useState(false);
    const [newTask, setNewTask] = useState<Partial<ProjectTask>>({
        title: '', description: '', project_id: '', status: 'todo'
    });

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            const [pjs, tsks] = await Promise.all([
                api.projects.list(),
                api.projects.tasks.list()
            ]);
            setProjects(pjs);
            setTasks(tsks);

            if (pjs.length > 0 && !newTask.project_id) {
                setNewTask(prev => ({ ...prev, project_id: pjs[0].id }));
            }
        } catch (error) {
            logError("proyectos/mis-tareas/page", error);
        } finally {
            setLoading(false);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    useEffect(() => { loadData(); }, [loadData]);

    const createTask = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await api.projects.tasks.create(newTask);
            setModalOpen(false);
            setNewTask(prev => ({ ...prev, title: '', description: '' }));
            loadData();
        } catch (err) { toast.error("Error al crear tarea"); }
    };

    const deleteTask = async (task: ProjectTask) => {
        if (!await showConfirm({ message: `¿Eliminar la tarea "${task.title}"?`, confirmLabel: "Eliminar", confirmVariant: "danger" })) return;
        try {
            await api.projects.tasks.delete(task.id);
            setTasks(prev => prev.filter(t => t.id !== task.id));
        } catch {
            toast.error("Error al eliminar la tarea");
        }
    };

    const moveTask = async (task: ProjectTask, direction: 1 | -1) => {
        const cIdx = STAGES.findIndex(s => s.id === task.status);
        if (cIdx === -1) return;

        const nIdx = cIdx + direction;
        if (nIdx < 0 || nIdx >= STAGES.length) return;

        const newStatus = STAGES[nIdx].id as any;
        setTasks(prev => prev.map(t => t.id === task.id ? { ...t, status: newStatus } : t));

        try {
            await api.projects.tasks.update(task.id, { status: newStatus });
        } catch (error) {
            setTasks(prev => prev.map(t => t.id === task.id ? { ...t, status: task.status } : t));
        }
    };

    return (
        <div className="flex flex-col h-[calc(100vh-2rem)] p-8 max-w-[1600px] mx-auto overflow-hidden animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex items-center justify-between gap-4 shrink-0 mb-6">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Mis Tareas</h1>
                    <p className="text-zinc-400">Board Kanban para tus tareas operativas de proyectos.</p>
                </div>
                <button
                    onClick={() => setModalOpen(true)}
                    className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl transition-all shadow-lg shadow-indigo-500/20 font-medium whitespace-nowrap"
                >
                    <Plus className="w-5 h-5" /> Nueva Tarea
                </button>
            </div>

            {/* Board */}
            <div className="flex-1 overflow-x-auto overflow-y-hidden rounded-2xl border border-white/5 bg-zinc-900/30 backdrop-blur-sm custom-scrollbar relative">
                {loading ? (
                    <div className="absolute inset-0 flex items-center justify-center">
                        <div className="animate-spin w-8 h-8 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full"></div>
                    </div>
                ) : (
                    <div className="flex h-full p-4 gap-4 min-w-max">
                        {STAGES.map((stage, idx) => {
                            const columnTasks = tasks.filter(t => t.status === stage.id);

                            return (
                                <div key={stage.id} className="w-80 flex flex-col h-full bg-[#111113]/80 rounded-xl border border-[#27272a] overflow-hidden shrink-0">
                                    <div className={cn("px-4 py-3 border-b border-[#27272a] shadow-sm flex items-center justify-between", stage.color)}>
                                        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                                            <span className={`w-2 h-2 rounded-full ${stage.dot}`} />
                                            {stage.label}
                                        </h3>
                                        <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-black/40 text-zinc-300">
                                            {columnTasks.length}
                                        </span>
                                    </div>

                                    <div className="flex-1 p-3 overflow-y-auto space-y-3 custom-scrollbar">
                                        {columnTasks.map(task => {
                                            const proj = projects.find(p => p.id === task.project_id);
                                            return (
                                                <div key={task.id} className="bg-zinc-800/50 border border-white/5 hover:border-white/10 rounded-lg p-3 group transition-all group">
                                                    <h4 className="text-sm font-medium text-white mb-1 leading-snug">{task.title}</h4>

                                                    <div className="flex items-center justify-between mt-3 text-xs">
                                                        <div className="flex items-center gap-1.5 text-zinc-400 bg-white/5 px-2 py-1 rounded-md border border-white/5 truncate max-w-[150px]">
                                                            <FolderGit2 className="w-3.5 h-3.5 shrink-0" />
                                                            <span className="truncate">{proj?.name || 'Desconocido'}</span>
                                                        </div>

                                                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                            <button
                                                                onClick={() => moveTask(task, -1)}
                                                                disabled={idx === 0}
                                                                className="p-1 text-zinc-500 hover:text-white disabled:opacity-0 transition-colors"
                                                            >
                                                                <ArrowRight className="w-4 h-4 rotate-180" />
                                                            </button>
                                                            <button
                                                                onClick={() => moveTask(task, 1)}
                                                                disabled={idx === STAGES.length - 1}
                                                                className="p-1 text-zinc-500 hover:text-white disabled:opacity-0 transition-colors"
                                                            >
                                                                <ArrowRight className="w-4 h-4" />
                                                            </button>
                                                            <button
                                                                onClick={() => deleteTask(task)}
                                                                className="p-1 text-zinc-500 hover:text-red-400 transition-colors"
                                                                title="Eliminar tarea"
                                                            >
                                                                <Trash2 className="w-3.5 h-3.5" />
                                                            </button>
                                                        </div>
                                                    </div>
                                                </div>
                                            )
                                        })}
                                        {columnTasks.length === 0 && (
                                            <div className="h-20 border-2 border-dashed border-[#27272a] rounded-lg flex items-center justify-center text-xs text-zinc-600 font-medium">
                                                Arrastra aquí
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                )}
            </div>

            {/* Modal */}
            {isModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
                    <div className="bg-[#111113] border border-[#27272a] rounded-2xl w-full max-w-md shadow-2xl overflow-hidden p-6">
                        <h3 className="text-lg font-semibold text-white mb-4">Nueva Tarea</h3>

                        {projects.length === 0 ? (
                            <div className="py-8 text-center bg-white/5 rounded-xl border border-white/10">
                                <p className="text-sm text-zinc-400 mb-4 px-6">Necesitas tener al menos un proyecto activo para crear tareas.</p>
                                <button onClick={() => setModalOpen(false)} className="text-sm text-white bg-white/10 hover:bg-white/20 px-4 py-2 rounded-lg">Cerrar</button>
                            </div>
                        ) : (
                            <form onSubmit={createTask} className="space-y-4">
                                <div>
                                    <label className="block text-sm text-zinc-400 mb-1">Título</label>
                                    <input required type="text" className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2 text-white outline-none focus:border-indigo-500"
                                        value={newTask.title} onChange={e => setNewTask({ ...newTask, title: e.target.value })} />
                                </div>

                                <div>
                                    <label className="block text-sm text-zinc-400 mb-1">Proyecto asociado</label>
                                    <select required className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2 text-white outline-none focus:border-indigo-500"
                                        value={newTask.project_id} onChange={e => setNewTask({ ...newTask, project_id: e.target.value })}>
                                        {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                                    </select>
                                </div>

                                <div>
                                    <label className="block text-sm text-zinc-400 mb-1">Descripción</label>
                                    <textarea className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2 text-white outline-none focus:border-indigo-500 h-20 resize-none"
                                        value={newTask.description || ''} onChange={e => setNewTask({ ...newTask, description: e.target.value })} />
                                </div>

                                <div className="flex justify-end gap-3 pt-4 border-t border-[#27272a]">
                                    <button type="button" onClick={() => setModalOpen(false)} className="px-4 py-2 text-zinc-400 hover:text-white">Cancelar</button>
                                    <button type="submit" className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl shadow-lg shadow-indigo-500/20">Agregar Tarea</button>
                                </div>
                            </form>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
