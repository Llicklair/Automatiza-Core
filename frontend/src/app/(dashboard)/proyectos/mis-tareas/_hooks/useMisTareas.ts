"use client";

import { useEffect, useState, useCallback } from "react";
import { api, type Project, type ProjectTask } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";

export const STAGES = [
    { id: 'todo', label: 'Por Hacer', color: 'border-border bg-muted', dot: 'bg-muted-foreground' },
    { id: 'in_progress', label: 'En Curso', color: 'border-blue-500/30 bg-blue-500/5', dot: 'bg-blue-400' },
    { id: 'done', label: 'Completado', color: 'border-emerald-500/30 bg-emerald-500/5', dot: 'bg-emerald-400' },
];

export function useMisTareas() {
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
        } catch { toast.error("Error al crear tarea"); }
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
        } catch {
            setTasks(prev => prev.map(t => t.id === task.id ? { ...t, status: task.status } : t));
        }
    };

    return {
        tasks, projects, loading,
        isModalOpen, setModalOpen,
        newTask, setNewTask,
        createTask, deleteTask, moveTask,
    };
}
