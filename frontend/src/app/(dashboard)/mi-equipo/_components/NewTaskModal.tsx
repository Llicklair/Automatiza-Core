"use client";

import type { AIEmployee } from "@/lib/api/ai_employees";
import { useTranslations } from "next-intl";
import { X, Bot, AlertCircle, Loader2 } from "lucide-react";
import { getCoordinatorOption } from "./task-constants";
import { DOMAIN_ICON } from "./EmployeeCard";

interface NewTaskModalProps {
    domain: string;
    setDomain: (d: string) => void;
    selectedEmployeeId: string | null;
    setSelectedEmployeeId: (id: string | null) => void;
    employees: AIEmployee[];
    intent: string;
    setIntent: (v: string) => void;
    creating: boolean;
    error: string;
    onClose: () => void;
    onSubmit: (e: React.FormEvent) => void;
}

export function NewTaskModal({
    domain, setDomain, selectedEmployeeId, setSelectedEmployeeId,
    employees, intent, setIntent, creating, error, onClose, onSubmit,
}: NewTaskModalProps) {
    const t = useTranslations("miEquipo");
    const tc = useTranslations("common");
    const COORDINATOR_OPTION = getCoordinatorOption(t);
    const handleClose = () => {
        onClose();
        setSelectedEmployeeId(null);
        setDomain("coordinator");
    };

    return (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" onClick={handleClose}>
            <div className="w-full max-w-lg rounded-2xl border border-border bg-card overflow-hidden"
                onClick={e => e.stopPropagation()}>
                <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                    <h2 className="font-semibold text-foreground text-base">{t("newTaskModal.title")}</h2>
                    <button onClick={handleClose} className="text-muted-foreground hover:text-foreground transition" aria-label={tc("close")}>
                        <X className="w-5 h-5" aria-hidden="true" />
                    </button>
                </div>

                <form onSubmit={onSubmit} className="p-6 space-y-4">
                    <div>
                        <label className="text-sm text-foreground block mb-2 font-medium">{t("newTaskModal.assignToLabel")}</label>
                        <div className="max-h-64 overflow-y-auto pr-0.5 space-y-2">
                            {/* Coordinator option */}
                            <button
                                type="button"
                                onClick={() => { setDomain(COORDINATOR_OPTION.value); setSelectedEmployeeId(null); }}
                                className={`w-full text-left p-3 rounded-xl border text-sm transition ${domain === COORDINATOR_OPTION.value && !selectedEmployeeId
                                    ? "border-purple-500 bg-purple-500/10 text-foreground ring-1 ring-purple-500/30"
                                    : "border-border bg-card text-muted-foreground hover:border-purple-500/50 hover:text-foreground"
                                    }`}
                            >
                                <p className="font-medium">{COORDINATOR_OPTION.label}</p>
                                <p className="text-[11px] mt-0.5 opacity-70">{COORDINATOR_OPTION.desc}</p>
                            </button>
                            {/* AI Employees */}
                            <div className="grid grid-cols-2 gap-2">
                            {employees.map(emp => {
                                const icon = emp.icon || (DOMAIN_ICON[emp.domain] ?? "🤖");
                                const isSelected = selectedEmployeeId === emp.id;
                                return (
                                    <button
                                        key={emp.id}
                                        type="button"
                                        onClick={() => { setDomain(emp.domain); setSelectedEmployeeId(emp.id); }}
                                        className={`text-left p-3 rounded-xl border text-sm transition flex flex-col gap-1 ${isSelected
                                            ? "border-primary bg-primary/10 text-foreground ring-1 ring-primary/30"
                                            : "border-border bg-card text-muted-foreground hover:border-border hover:text-foreground"
                                            } ${emp.status === "paused" ? "opacity-50 cursor-not-allowed" : ""}`}
                                        disabled={emp.status === "paused"}
                                    >
                                        <span className="text-xl leading-none">{icon}</span>
                                        <p className="font-medium text-xs mt-0.5 truncate">{emp.name}</p>
                                        <p className="text-[10px] opacity-60 truncate">{emp.role}</p>
                                    </button>
                                );
                            })}
                            </div>
                        </div>
                    </div>

                    <div>
                        <label className="text-sm text-foreground block mb-1.5 font-medium">
                            {t("newTaskModal.intentLabel")}
                        </label>
                        <textarea
                            rows={4}
                            required
                            value={intent}
                            onChange={e => setIntent(e.target.value)}
                            placeholder={
                                domain === "coordinator" ? t("newTaskModal.placeholderCoordinator") :
                                    domain === "billing" ? t("newTaskModal.placeholderBilling") :
                                        domain === "documents" ? t("newTaskModal.placeholderDocuments") :
                                            domain === "hr" ? t("newTaskModal.placeholderHr") :
                                                domain === "compliance" ? t("newTaskModal.placeholderCompliance") :
                                                    t("newTaskModal.placeholderDefault")
                            }
                            className="w-full px-3 py-2.5 rounded-xl bg-card border border-border text-foreground text-sm placeholder:text-muted-foreground resize-none focus:outline-none focus:ring-2 focus:ring-primary transition"
                        />
                    </div>

                    {error && (
                        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                            <p className="text-sm text-red-400">{error}</p>
                        </div>
                    )}

                    <div className="flex gap-3 pt-1">
                        <button
                            type="button"
                            onClick={handleClose}
                            className="flex-1 py-2.5 rounded-xl border border-border text-muted-foreground hover:text-foreground text-sm transition"
                        >
                            {tc("cancel")}
                        </button>
                        <button
                            type="submit"
                            disabled={creating || !intent.trim()}
                            className="flex-1 py-2.5 rounded-xl bg-primary hover:bg-primary disabled:opacity-50 text-foreground text-sm font-medium transition flex items-center justify-center gap-2"
                        >
                            {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Bot className="w-4 h-4" />}
                            {creating ? t("newTaskModal.submitting") : t("newTaskModal.submit")}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
