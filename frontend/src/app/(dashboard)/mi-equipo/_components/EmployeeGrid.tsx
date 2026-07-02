"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import type { AIEmployee } from "@/lib/api/ai_employees";
import { Plus, Users2, AlertCircle } from "lucide-react";
import { EmployeeCard } from "./EmployeeCard";
import { InstructModal } from "./InstructModal";
import { NewEmployeeModal } from "./NewEmployeeModal";
import { showConfirm } from "@/stores/confirm";
import { useToastStore } from "@/stores/toast";

interface EmployeeGridProps {
    employees: AIEmployee[];
    loading: boolean;
    onRefresh: () => void;
    refreshing: boolean;
}

export function EmployeeGrid({ employees, loading, onRefresh, refreshing }: EmployeeGridProps) {
    const t = useTranslations("miEquipo");
    const tc = useTranslations("common");
    const [showNewModal, setShowNewModal] = useState(false);
    const [instructTarget, setInstructTarget] = useState<AIEmployee | null>(null);
    const [seeding, setSeeding] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const toast = useToastStore();

    const handleSeed = async () => {
        setSeeding(true);
        try { await api.aiEmployees.seed(); onRefresh(); toast.success(t("grid.toastSeedCreated")); }
        catch { toast.error(t("grid.toastSeedError")); }
        finally { setSeeding(false); }
    };

    const handleToggle = async (id: string, current: AIEmployee["status"]) => {
        const next = current === "paused" ? "idle" : "paused";
        try {
            await api.aiEmployees.updateStatus(id, next);
            onRefresh();
        } catch {
            toast.error(t("grid.toastStatusError"));
        }
    };

    const handleDelete = async (id: string) => {
        const emp = employees.find(e => e.id === id);
        if (!(await showConfirm({
            message: t("grid.deleteConfirm", { name: emp?.name ?? t("grid.deleteFallbackName") }),
            confirmLabel: tc("delete"),
            confirmVariant: "danger",
        }))) return;
        try { await api.aiEmployees.delete(id); onRefresh(); }
        catch { toast.error(t("grid.toastDeleteError")); }
    };

    if (loading) return (
        <div className="flex items-center justify-center h-64">
            <div className="w-7 h-7 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
        </div>
    );

    return (
        <>
            {instructTarget && <InstructModal employee={instructTarget} onClose={() => setInstructTarget(null)}
                onSent={() => { toast.success(t("grid.toastInstructionSent", { name: instructTarget.name })); onRefresh(); }} />}
            {showNewModal && <NewEmployeeModal onClose={() => setShowNewModal(false)}
                onCreated={() => { onRefresh(); toast.success(t("grid.toastEmployeeCreated")); }} />}

            {error && (
                <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">
                    <AlertCircle className="w-4 h-4 shrink-0" /> {error}
                </div>
            )}

            {/* Boton nueva IA */}
            <div className="flex justify-end mb-4">
                <button onClick={() => setShowNewModal(true)}
                    className="flex items-center gap-2 px-3 py-1.5 bg-violet-600 hover:bg-violet-500 text-foreground rounded-lg text-xs font-medium transition-colors">
                    <Plus className="w-3.5 h-3.5" /> {t("grid.newAi")}
                </button>
            </div>

            {employees.length === 0 ? (
                <div className="text-center py-16 border-2 border-dashed border-border rounded-xl">
                    <Users2 className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
                    <p className="text-muted-foreground font-medium text-sm">{t("grid.emptyTitle")}</p>
                    <p className="text-xs text-muted-foreground mt-1">{t("grid.emptyDescription")}</p>
                    <button onClick={handleSeed} disabled={seeding}
                        className="mt-4 px-5 py-2 bg-violet-600 hover:bg-violet-500 text-foreground rounded-lg text-sm font-medium disabled:opacity-60 transition-colors">
                        {seeding ? t("grid.seedingButton") : t("grid.seedButton")}
                    </button>
                </div>
            ) : (
                <>
                    <div>
                        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                            {t("grid.orgChartHeader", { count: employees.length })}
                        </p>
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                            {employees.map(emp => (
                                <EmployeeCard key={emp.id} employee={emp} onToggle={handleToggle} onInstruct={setInstructTarget} onDelete={handleDelete} />
                            ))}
                        </div>
                    </div>
                    <div className="flex items-center justify-between pt-2 border-t border-border mt-4">
                        <p className="text-xs text-muted-foreground">{t("grid.activityHint")}</p>
                        <a href="/bandeja?tab=actividad" className="text-xs text-violet-400 hover:text-violet-300 transition-colors">
                            {t("grid.viewInbox")}
                        </a>
                    </div>
                </>
            )}
        </>
    );
}
