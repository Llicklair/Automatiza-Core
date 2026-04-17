"use client";

import { Plus, ArrowRight, FolderGit2, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useMisTareas, STAGES } from "./_hooks/useMisTareas";
import { NewTaskModal } from "./_components/NewTaskModal";

export default function ProjectTasksPage() {
    const {
        tasks, projects, loading,
        isModalOpen, setModalOpen,
        newTask, setNewTask,
        createTask, deleteTask, moveTask,
    } = useMisTareas();

    return (
        <div className="flex flex-col h-[calc(100vh-2rem)] p-8 max-w-[1600px] mx-auto overflow-hidden animate-in fade-in duration-500">
            <div className="flex items-center justify-between gap-4 shrink-0 mb-6">
                <div>
                    <h1 className="text-3xl font-bold text-foreground mb-2">Mis Tareas</h1>
                    <p className="text-muted-foreground">Board Kanban para tus tareas operativas de proyectos.</p>
                </div>
                <button
                    onClick={() => setModalOpen(true)}
                    className="inline-flex items-center gap-2 bg-primary hover:bg-primary text-foreground px-5 py-2.5 rounded-xl transition-all shadow-lg shadow-primary/20 font-medium whitespace-nowrap"
                >
                    <Plus className="w-5 h-5" /> Nueva Tarea
                </button>
            </div>

            <div className="flex-1 overflow-x-auto overflow-y-hidden rounded-2xl border border-border bg-card backdrop-blur-sm custom-scrollbar relative">
                {loading ? (
                    <div className="absolute inset-0 flex items-center justify-center">
                        <div className="animate-spin w-8 h-8 border-2 border-primary/20 border-t-indigo-500 rounded-full"></div>
                    </div>
                ) : (
                    <div className="flex h-full p-4 gap-4 min-w-max">
                        {STAGES.map((stage, idx) => {
                            const columnTasks = tasks.filter(t => t.status === stage.id);

                            return (
                                <div key={stage.id} className="w-80 flex flex-col h-full bg-card/80 rounded-xl border border-border overflow-hidden shrink-0">
                                    <div className={cn("px-4 py-3 border-b border-border shadow-sm flex items-center justify-between", stage.color)}>
                                        <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                                            <span className={`w-2 h-2 rounded-full ${stage.dot}`} />
                                            {stage.label}
                                        </h3>
                                        <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-muted text-foreground">
                                            {columnTasks.length}
                                        </span>
                                    </div>

                                    <div className="flex-1 p-3 overflow-y-auto space-y-3 custom-scrollbar">
                                        {columnTasks.map(task => {
                                            const proj = projects.find(p => p.id === task.project_id);
                                            return (
                                                <div key={task.id} className="bg-muted border border-border hover:border-border rounded-lg p-3 group transition-all group">
                                                    <h4 className="text-sm font-medium text-foreground mb-1 leading-snug">{task.title}</h4>

                                                    <div className="flex items-center justify-between mt-3 text-xs">
                                                        <div className="flex items-center gap-1.5 text-muted-foreground bg-accent/50 px-2 py-1 rounded-md border border-border truncate max-w-[150px]">
                                                            <FolderGit2 className="w-3.5 h-3.5 shrink-0" />
                                                            <span className="truncate">{proj?.name || 'Desconocido'}</span>
                                                        </div>

                                                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                            <button
                                                                onClick={() => moveTask(task, -1)}
                                                                disabled={idx === 0}
                                                                className="p-1 text-muted-foreground hover:text-foreground disabled:opacity-0 transition-colors"
                                                            >
                                                                <ArrowRight className="w-4 h-4 rotate-180" />
                                                            </button>
                                                            <button
                                                                onClick={() => moveTask(task, 1)}
                                                                disabled={idx === STAGES.length - 1}
                                                                className="p-1 text-muted-foreground hover:text-foreground disabled:opacity-0 transition-colors"
                                                            >
                                                                <ArrowRight className="w-4 h-4" />
                                                            </button>
                                                            <button
                                                                onClick={() => deleteTask(task)}
                                                                className="p-1 text-muted-foreground hover:text-red-400 transition-colors"
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
                                            <div className="h-20 border-2 border-dashed border-border rounded-lg flex items-center justify-center text-xs text-muted-foreground font-medium">
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

            {isModalOpen && (
                <NewTaskModal
                    newTask={newTask}
                    projects={projects}
                    onChange={setNewTask}
                    onSubmit={createTask}
                    onClose={() => setModalOpen(false)}
                />
            )}
        </div>
    );
}
