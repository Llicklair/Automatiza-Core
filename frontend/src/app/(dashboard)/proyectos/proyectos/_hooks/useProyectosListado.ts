"use client";

import { useEffect, useState, useRef } from "react";
import { api, type Project } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";
import { PlayCircle, CheckCircle2, Clock } from "lucide-react";

export const statusConfig: Record<string, { label: string; bg: string; text: string; icon: any }> = {
    active: { label: "Activo", bg: "bg-blue-500/10", text: "text-blue-400", icon: PlayCircle },
    completed: { label: "Completado", bg: "bg-emerald-500/10", text: "text-emerald-400", icon: CheckCircle2 },
    on_hold: { label: "En Pausa", bg: "bg-amber-500/10", text: "text-amber-400", icon: Clock },
};

export function useProyectosListado() {
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
        createProject, saveEdit, deleteProject, openEditModal,
    };
}
