"use client";

import { useEffect, useState, useRef } from "react";
import { useTranslations } from "next-intl";
import { api, type Project } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";
import { PlayCircle, CheckCircle2, Clock } from "lucide-react";

type Translator = (key: string, values?: Record<string, string | number>) => string;

export const getStatusConfig = (t: Translator): Record<string, { label: string; bg: string; text: string; icon: any }> => ({
    active: { label: t("status.active"), bg: "bg-blue-500/10", text: "text-blue-400", icon: PlayCircle },
    completed: { label: t("status.completed"), bg: "bg-emerald-500/10", text: "text-emerald-400", icon: CheckCircle2 },
    on_hold: { label: t("status.onHold"), bg: "bg-amber-500/10", text: "text-amber-400", icon: Clock },
});

// Backward-compatible export (labels are resolved via getStatusConfig / hook return once consumers migrate).
export const statusConfig: Record<string, { label: string; bg: string; text: string; icon: any }> = {
    active: { label: "active", bg: "bg-blue-500/10", text: "text-blue-400", icon: PlayCircle },
    completed: { label: "completed", bg: "bg-emerald-500/10", text: "text-emerald-400", icon: CheckCircle2 },
    on_hold: { label: "on_hold", bg: "bg-amber-500/10", text: "text-amber-400", icon: Clock },
};

export function useProyectosListado() {
    const t = useTranslations("proyectos");
    const tc = useTranslations("common");
    const toast = useToastStore();
    const statusConfig = getStatusConfig(t);
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
        } catch { toast.error(t("listado.createError")); }
    };

    const saveEdit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editProject) return;
        try {
            await api.projects.update(editProject.id, editForm);
            setEditProject(null);
            loadData();
        } catch { toast.error(t("listado.updateError")); }
    };

    const deleteProject = async (project: Project) => {
        if (!await showConfirm({ message: t("listado.deleteConfirm", { name: project.name }), confirmLabel: tc("delete"), confirmVariant: "danger" })) return;
        try {
            await api.projects.delete(project.id);
            loadData();
        } catch { toast.error(t("listado.deleteError")); }
    };

    const openEditModal = (project: Project) => {
        setEditProject(project);
        setEditForm({ name: project.name, description: project.description, budget: project.budget, status: project.status });
        setOpenMenuId(null);
    };

    return {
        projects, loading,
        isCreateOpen, setCreateOpen,
        newProject, setNewProject,
        editProject, setEditProject,
        editForm, setEditForm,
        openMenuId, setOpenMenuId,
        menuRef,
        statusConfig,
        createProject, saveEdit, deleteProject, openEditModal,
    };
}
