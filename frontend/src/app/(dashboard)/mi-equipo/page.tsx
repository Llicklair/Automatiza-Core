"use client";

import { useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import type { AIEmployee } from "@/lib/api/ai_employees";
import { Bot, RefreshCw, Plus, Users2, AlertCircle, Sparkles } from "lucide-react";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { EmployeeCard } from "./_components/EmployeeCard";
import { InstructModal } from "./_components/InstructModal";
import { NewEmployeeModal } from "./_components/NewEmployeeModal";
import { TaskPanel } from "./_components/TaskPanel";

const TABS = [
    { key: "tareas", label: "Tareas", icon: Sparkles },
    { key: "equipo", label: "Equipo IA", icon: Users2 },
] as const;

type TabKey = (typeof TABS)[number]["key"];

export default function TareasPage() {
    const searchParams = useSearchParams();
    const initialTab = TABS.some(t => t.key === searchParams.get("tab")) ? searchParams.get("tab") as TabKey : "tareas";
    const [activeTab, setActiveTab] = useState<TabKey>(initialTab);

    const [employees, setEmployees] = useState<AIEmployee[]>([]);
    const [loading, setLoading] = useState(true);
    const [seeding, setSeeding] = useState(false);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [instructTarget, setInstructTarget] = useState<AIEmployee | null>(null);
    const [showNewModal, setShowNewModal] = useState(false);
    const toast = useToastStore();

    const BUILTIN_COUNT = 8;

    const loadData = useCallback(async () => {
        try {
            let emps = await api.aiEmployees.list();
            // Auto-seed si faltan built-ins (nuevos dominios añadidos al equipo predefinido)
            const builtinCount = emps.filter(e => e.is_builtin).length;
            if (builtinCount < BUILTIN_COUNT) {
                await api.aiEmployees.seed();
                emps = await api.aiEmployees.list();
            }
            setEmployees(emps); setError(null);
        }
        catch (e: any) { setError(e?.message ?? "Error cargando datos"); }
        finally { setLoading(false); }
    }, []);

    // Solo cargar empleados cuando la tab equipo esté activa
    useEffect(() => {
        if (activeTab !== "equipo") return;
        loadData();
        const interval = setInterval(loadData, 15_000);
        return () => clearInterval(interval);
    }, [loadData, activeTab]);

    const handleSeed = async () => {
        setSeeding(true);
        try { await api.aiEmployees.seed(); await loadData(); toast.success("Equipo inicial creado"); }
        catch { toast.error("Error al crear equipo inicial"); }
        finally { setSeeding(false); }
    };

    const handleToggle = async (id: string, current: AIEmployee["status"]) => {
        const next = current === "paused" ? "idle" : "paused";
        setEmployees(prev => prev.map(e => e.id === id ? { ...e, status: next } : e));
        try { await api.aiEmployees.updateStatus(id, next); }
        catch {
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
        try { await api.aiEmployees.updateAppearance(id, { icon, avatar_color: color }); }
        catch { loadData(); }
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
        try { await api.aiEmployees.delete(id); }
        catch {
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

    return (
        <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
            {instructTarget && <InstructModal employee={instructTarget} onClose={() => setInstructTarget(null)}
                onSent={() => { toast.success(`Instrucción enviada a ${instructTarget.name}`); loadData(); }} />}
            {showNewModal && <NewEmployeeModal onClose={() => setShowNewModal(false)}
                onCreated={() => { loadData(); toast.success("Empleado IA creado"); }} />}

            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-xl font-semibold text-foreground flex items-center gap-2">
                        <Sparkles className="w-6 h-6 text-violet-400" /> Tareas
                    </h1>
                    <p className="text-xs text-muted-foreground mt-1">Asigna tareas a tus agentes y gestiona tu equipo IA</p>
                </div>
                <div className="flex gap-2">
                    {activeTab === "equipo" && (
                        <>
                            <button onClick={() => { setRefreshing(true); loadData().finally(() => setRefreshing(false)); }}
                                className="p-2 rounded-lg border border-border hover:bg-muted text-muted-foreground transition-colors">
                                <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
                            </button>
                            <button onClick={() => setShowNewModal(true)}
                                className="flex items-center gap-2 px-3 py-1.5 bg-violet-600 hover:bg-violet-500 text-foreground rounded-lg text-xs font-medium transition-colors">
                                <Plus className="w-3.5 h-3.5" /> Nueva IA
                            </button>
                        </>
                    )}
                </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 border-b border-border">
                {TABS.map(tab => {
                    const Icon = tab.icon;
                    const isActive = activeTab === tab.key;
                    return (
                        <button
                            key={tab.key}
                            onClick={() => switchTab(tab.key)}
                            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
                                isActive
                                    ? "border-violet-500 text-foreground"
                                    : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
                            }`}
                        >
                            <Icon className="w-4 h-4" />
                            {tab.label}
                        </button>
                    );
                })}
            </div>

            {error && activeTab === "equipo" && (
                <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">
                    <AlertCircle className="w-4 h-4 shrink-0" /> {error}
                </div>
            )}

            {/* Tab content */}
            {activeTab === "equipo" && (
                <>
                    {loading ? (
                        <div className="flex items-center justify-center h-48">
                            <div className="w-7 h-7 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
                        </div>
                    ) : employees.length === 0 ? (
                        <div className="text-center py-16 border-2 border-dashed border-border rounded-xl">
                            <Users2 className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
                            <p className="text-muted-foreground font-medium text-sm">Sin empleados aún</p>
                            <p className="text-xs text-muted-foreground mt-1">Crea el equipo inicial con Ana, Carlos y Sofía</p>
                            <button onClick={handleSeed} disabled={seeding}
                                className="mt-4 px-5 py-2 bg-violet-600 hover:bg-violet-500 text-foreground rounded-lg text-sm font-medium disabled:opacity-60 transition-colors">
                                {seeding ? "Creando…" : "Crear equipo inicial"}
                            </button>
                        </div>
                    ) : (
                        <>
                            <div>
                                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                                    Organigrama · {employees.length} empleados
                                </p>
                                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                                    {employees.map(emp => (
                                        <EmployeeCard key={emp.id} employee={emp} onToggle={handleToggle} onInstruct={setInstructTarget} onDelete={handleDelete} onAppearanceChange={handleAppearanceChange} />
                                    ))}
                                </div>
                            </div>
                            <div className="flex items-center justify-between pt-2 border-t border-border">
                                <p className="text-xs text-muted-foreground">Las actividades de tus agentes aparecen en la bandeja</p>
                                <a href="/bandeja?tab=actividad" className="text-xs text-violet-400 hover:text-violet-300 transition-colors">
                                    Ver bandeja de agentes →
                                </a>
                            </div>
                        </>
                    )}
                </>
            )}

            {activeTab === "tareas" && (
                <TaskPanel isActive={activeTab === "tareas"} />
            )}
        </div>
    );
}
