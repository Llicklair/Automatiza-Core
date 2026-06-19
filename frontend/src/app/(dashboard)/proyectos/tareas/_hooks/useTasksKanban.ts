import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { api, ProjectTask } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";

export type TaskStatus = 'todo' | 'in_progress' | 'done';

export function useTasksKanban() {
    const t = useTranslations("proyectos");
    const tc = useTranslations("common");
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

    // Menu contextual
    const [openMenuId, setOpenMenuId] = useState<string | null>(null);

    // Cierra menu al hacer clic fuera
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

    // eslint-disable-next-line react-hooks/exhaustive-deps
    useEffect(() => { loadData(); }, [projectId]);

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
            toast.error(t("tasksKanban.createError"));
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
            toast.error(t("tasksKanban.saveError"));
        } finally {
            setEditSaving(false);
        }
    };

    const handleDelete = async (task: ProjectTask) => {
        setOpenMenuId(null);
        if (!await showConfirm({ message: t("tasksKanban.deleteConfirm", { title: task.title }), confirmLabel: tc("delete"), confirmVariant: "danger" })) return;
        try {
            await api.projects.tasks.delete(task.id);
            setTasks(prev => prev.filter(t => t.id !== task.id));
        } catch {
            toast.error(t("tasksKanban.deleteError"));
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

    return {
        tasks, isLoading, draggedTask,
        showModal, setShowModal, saving, title, setTitle, description, setDescription, dueDate, setDueDate,
        editTask, setEditTask, editTitle, setEditTitle, editDescription, setEditDescription, editDueDate, setEditDueDate, editSaving,
        openMenuId, setOpenMenuId,
        handleCreate, handleEditOpen, handleEditSave, handleDelete,
        handleDragStart, handleDragEnd, handleDragOver, handleDrop,
        getTasksByStatus,
    };
}
