"use client";

import { RefreshCw, Plus, Users2, AlertCircle, Sparkles } from "lucide-react";
import { EmployeeCard } from "./_components/EmployeeCard";
import { InstructModal } from "./_components/InstructModal";
import { NewEmployeeModal } from "./_components/NewEmployeeModal";
import { TaskPanel } from "./_components/TaskPanel";
import { useMiEquipo } from "./_hooks/useMiEquipo";
import { useToastStore } from "@/stores/toast";
import { LlmNotConfiguredBanner } from "@/components/shared/LlmNotConfiguredBanner";
import { PageContainer } from "@/components/shared/PageContainer";

export default function TareasPage() {
    const {
        TABS, activeTab, employees, loading, seeding, refreshing, error,
        instructTarget, setInstructTarget, showNewModal, setShowNewModal,
        loadData, handleSeed, handleToggle, handleAppearanceChange, handleDelete,
        switchTab, handleRefresh,
    } = useMiEquipo();
    const toast = useToastStore();

    return (
        <PageContainer width="6xl">
            {instructTarget && (
                <InstructModal
                    employee={instructTarget}
                    onClose={() => setInstructTarget(null)}
                    onSent={() => { toast.success(`Instrucción enviada a ${instructTarget.name}`); loadData(); }}
                />
            )}
            {showNewModal && (
                <NewEmployeeModal
                    onClose={() => setShowNewModal(false)}
                    onCreated={() => { loadData(); toast.success("Empleado IA creado"); }}
                />
            )}

            <LlmNotConfiguredBanner />

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
                            <button
                                onClick={handleRefresh}
                                className="p-2 rounded-lg border border-border hover:bg-muted text-muted-foreground transition-colors"
                             aria-label="Actualizar equipo">
                                <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} aria-hidden="true" />
                            </button>
                            <button
                                onClick={() => setShowNewModal(true)}
                                className="flex items-center gap-2 px-3 py-1.5 bg-violet-600 hover:bg-violet-500 text-foreground rounded-lg text-xs font-medium transition-colors"
                            >
                                <Plus className="w-3.5 h-3.5" /> Nueva IA
                            </button>
                        </>
                    )}
                </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 border-b border-border">
                {TABS.map(tab => {
                    const Icon = tab.key === "tareas" ? Sparkles : Users2;
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
                            <button
                                onClick={handleSeed}
                                disabled={seeding}
                                className="mt-4 px-5 py-2 bg-violet-600 hover:bg-violet-500 text-foreground rounded-lg text-sm font-medium disabled:opacity-60 transition-colors"
                            >
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
                                        <EmployeeCard
                                            key={emp.id}
                                            employee={emp}
                                            onToggle={handleToggle}
                                            onInstruct={setInstructTarget}
                                            onDelete={handleDelete}
                                            onAppearanceChange={handleAppearanceChange}
                                        />
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
        </PageContainer>
    );
}
