"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api, Project } from "@/lib/api";
import { addDays, differenceInDays, isAfter, isBefore } from "date-fns";
import { logError } from "@/lib/logger";
import { PlayCircle, CheckCircle2, Clock } from "lucide-react";

export function useProjectsPage() {
    const t = useTranslations("proyectos");
    const [projects, setProjects] = useState<Project[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");
    const [search, setSearch] = useState("");

    const [form, setForm] = useState({
        name: "", description: "", budget: "",
        start_date: "", due_date: "", status: "active"
    });

    const viewStart = addDays(new Date(), -10);
    const viewEnd = addDays(new Date(), 40);
    const totalDays = differenceInDays(viewEnd, viewStart);

    const loadData = async () => {
        setIsLoading(true);
        try {
            const data = await api.projects.list();
            setProjects(data);
        } catch (error) { logError("proyectos/page", error); }
        finally { setIsLoading(false); }
    };

    useEffect(() => { loadData(); }, []);

    const openModal = () => {
        setForm({ name: "", description: "", budget: "", start_date: "", due_date: "", status: "active" });
        setError("");
        setShowModal(true);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.name.trim()) return;
        setSaving(true);
        setError("");
        try {
            await api.projects.create({
                name: form.name,
                description: form.description || undefined,
                budget: form.budget ? parseFloat(form.budget) : 0,
                status: form.status,
                start_date: form.start_date || undefined,
                due_date: form.due_date || undefined,
            });
            setShowModal(false);
            await loadData();
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : t("page.createError"));
        } finally {
            setSaving(false);
        }
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'active': return { icon: PlayCircle, className: "flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20", label: t("status.active") };
            case 'completed': return { icon: CheckCircle2, className: "flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20", label: t("status.completed") };
            case 'on_hold': return { icon: Clock, className: "flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-500 border border-amber-500/20", label: t("status.onHold") };
            default: return null;
        }
    };

    const getGanttBarStyle = (start: string | null, due: string | null, status: string) => {
        if (!start || !due) return { display: 'none' as const };
        const dStart = new Date(start);
        const dEnd = new Date(due);
        const visualStart = isBefore(dStart, viewStart) ? viewStart : dStart;
        const visualEnd = isAfter(dEnd, viewEnd) ? viewEnd : dEnd;
        if (isAfter(dStart, viewEnd) || isBefore(dEnd, viewStart)) return { display: 'none' as const };
        const leftPct = (differenceInDays(visualStart, viewStart) / totalDays) * 100;
        const widthPct = (differenceInDays(visualEnd, visualStart) / totalDays) * 100;
        let bg = "linear-gradient(90deg, #3b82f6, #60a5fa)";
        if (status === 'completed') bg = "linear-gradient(90deg, #10b981, #34d399)";
        if (status === 'on_hold') bg = "linear-gradient(90deg, #f59e0b, #fbbf24)";
        return { left: `${Math.max(0, leftPct)}%`, width: `${Math.max(2, widthPct)}%`, background: bg };
    };

    const filtered = projects.filter(p =>
        p.name.toLowerCase().includes(search.toLowerCase())
    );

    return {
        projects, isLoading,
        showModal, setShowModal,
        saving, error,
        search, setSearch,
        form, setForm,
        viewStart, viewEnd,
        filtered,
        openModal, handleSubmit, getStatusBadge, getGanttBarStyle,
    };
}
