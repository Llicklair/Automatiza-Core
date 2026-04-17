"use client";

import { useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import type { AIEmployee } from "@/lib/api/ai_employees";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";

const TABS = [
    { key: "tareas", label: "Tareas" },
    { key: "equipo", label: "Equipo IA" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

const BUILTIN_COUNT = 8;

export function useMiEquipo() {
    const searchParams = useSearchParams();
    const initialTab = TABS.some(t => t.key === searchParams.get("tab"))
        ? searchParams.get("tab") as TabKey
        : "tareas";

    const [activeTab, setActiveTab] = useState<TabKey>(initialTab);
    const [employees, setEmployees] = useState<AIEmployee[]>([]);
    const [loading, setLoading] = useState(true);
    const [seeding, setSeeding] = useState(false);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [instructTarget, setInstructTarget] = useState<AIEmployee | null>(null);
    const [showNewModal, setShowNewModal] = useState(false);
    const toast = useToastStore();

    const loadData = useCallback(async () => {
        try {
            let emps = await api.aiEmployees.list();
            const builtinCount = emps.filter(e => e.is_builtin).length;
            if (builtinCount < BUILTIN_COUNT) {
                await api.aiEmployees.seed();
                emps = await api.aiEmployees.list();
            }
            setEmployees(emps);
            setError(null);
        } catch (e: any) {
            setError(e?.message ?? "Error cargando datos");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (activeTab !== "equipo") return;
        loadData();
        const interval = setInterval(loadData, 15_000);
        return () => clearInterval(interval);
    }, [loadData, activeTab]);

    const handleSeed = async () => {
        setSeeding(true);
        try {
            await api.aiEmployees.seed();
            await loadData();
            toast.success("Equipo inicial creado");
        } catch {
            toast.error("Error al crear equipo inicial");
        } finally {
            setSeeding(false);
        }
    };

    const handleToggle = async (id: string, current: AIEmployee["status"]) => {
        const next = current === "paused" ? "idle" : "paused";
        setEmployees(prev => prev.map(e => e.id === id ? { ...e, status: next } : e));
        try {
            await api.aiEmployees.updateStatus(id, next);
        } catch {
            setEmployees(prev => prev.map(e => e.id === id ? { ...e, status: current } : e));
            toast.error("Error al cambiar estado del agente");
        }
    };

    const handleAppearanceChange = async (id: string, icon?: string, color?: string) => {
        setEmployees(prev => prev.map(e => e.id === id ? {
            ...e,
            ...(icon ? { icon } : {}),
            ...(color ? { avatar_color: color } : {}),
        } : e));
        try {
            await api.aiEmployees.updateAppearance(id, { icon, avatar_color: color });
        } catch {
            loadData();
        }
    };

    const handleDelete = async (id: string) => {
        const emp = employees.find(e => e.id === id);
        const confirmed = await showConfirm({
            message: `¿Eliminar a ${emp?.name ?? "este empleado"}? Esta acción no se puede deshacer.`,
            confirmLabel: "Eliminar",
            confirmVariant: "danger",
        });
        if (!confirmed) return;
        setEmployees(prev => prev.filter(e => e.id !== id));
        try {
            await api.aiEmployees.delete(id);
        } catch {
            toast.error("Error al eliminar el empleado");
            loadData();
        }
    };

    const switchTab = (tab: TabKey) => {
        setActiveTab(tab);
        const url = new URL(window.location.href);
        url.searchParams.set("tab", tab);
        window.history.replaceState(null, "", url.toString());
    };

    const handleRefresh = async () => {
        setRefreshing(true);
        await loadData();
        setRefreshing(false);
    };

    return {
        TABS,
        activeTab,
        employees,
        loading,
        seeding,
        refreshing,
        error,
        instructTarget,
        setInstructTarget,
        showNewModal,
        setShowNewModal,
        loadData,
        handleSeed,
        handleToggle,
        handleAppearanceChange,
        handleDelete,
        switchTab,
        handleRefresh,
    };
}
