"use client";

import { useEffect, useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { api, type Project, type ProjectTask } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";

// Stage metadata is locale-independent (id/color/dot). The visible label is
// resolved per-locale in the component via the `proyectos.misTareas.stage*` keys.
export const STAGES = [
    { id: 'todo', label: 'todo', color: 'border-border bg-muted', dot: 'bg-muted-foreground' },
    { id: 'in_progress', label: 'in_progress', color: 'border-blue-500/30 bg-blue-500/5', dot: 'bg-blue-400' },
    { id: 'done', label: 'done', color: 'border-emerald-500/30 bg-emerald-500/5', dot: 'bg-emerald-400' },
];

export function useMisTareas() {
    const t = useTranslations("proyectos");
    const tc = useTranslations("common");
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
        } catch { toast.error(t("misTareas.createError")); }
    };

    const deleteTask = async (task: ProjectTask) => {
        if (!await showConfirm({ message: t("misTareas.deleteConfirm", { title: task.title }), confirmLabel: tc("delete"), confirmVariant: "danger" })) return;
        try {
            await api.projects.tasks.delete(task.id);
            setTasks(prev => prev.filter(tk => tk.id !== task.id));
        } catch {
            toast.error(t("misTareas.deleteError"));
        }
    };

    const moveTask = async (task: ProjectTask, direction: 1 | -1) => {
        const cIdx = STAGES.findIndex(s => s.id === task.status);
        if (cIdx === -1) return;

        const nIdx = cIdx + direction;
        if (nIdx < 0 || nIdx >= STAGES.length) return;

        const newStatus = STAGES[nIdx].id as any;
        setTasks(prev => prev.map(tk => tk.id === task.id ? { ...tk, status: newStatus } : tk));

        try {
            await api.projects.tasks.update(task.id, { status: newStatus });
        } catch {
            setTasks(prev => prev.map(tk => tk.id === task.id ? { ...tk, status: task.status } : tk));
        }
    };

    return {
        tasks, projects, loading,
        isModalOpen, setModalOpen,
        newTask, setNewTask,
        createTask, deleteTask, moveTask,
    };
}
