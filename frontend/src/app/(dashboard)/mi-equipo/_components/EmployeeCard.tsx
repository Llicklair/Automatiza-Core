"use client";

import { useEffect, useState } from "react";
import { aiEmployees, type AIEmployee } from "@/lib/api/ai_employees";
import { MessageSquare, Trash2, Pencil } from "lucide-react";
import { AppearancePicker, getAvatarClasses } from "./IconPicker";
import { UsageModal } from "./UsageModal";

function BudgetBar({ employee, limit }: { employee: AIEmployee; limit: number }) {
    const [spent, setSpent] = useState<number | null>(null);
    const [modalOpen, setModalOpen] = useState(false);

    useEffect(() => {
        let cancelled = false;
        aiEmployees.usage(employee.id, { limit: 1 })
            .then(r => { if (!cancelled) setSpent(r.total_cost_usd); })
            .catch(() => { if (!cancelled) setSpent(0); });
        return () => { cancelled = true; };
    }, [employee.id]);

    if (spent === null) return null;
    const pct = Math.min(100, (spent / limit) * 100);
    const color = pct >= 90 ? "bg-red-500" : pct >= 70 ? "bg-amber-500" : "bg-emerald-500";
    const textColor = pct >= 90 ? "text-red-400" : pct >= 70 ? "text-amber-400" : "text-muted-foreground";

    return (
        <>
            <button
                onClick={() => setModalOpen(true)}
                title="Ver historial de consumo"
                className="flex flex-col gap-1 pt-2 border-t border-border w-full text-left hover:opacity-80 transition-opacity"
            >
                <div className={`flex items-center justify-between text-[10px] ${textColor}`}>
                    <span>Presupuesto</span>
                    <span className="font-medium">${spent.toFixed(2)} / ${limit.toFixed(2)}</span>
                </div>
                <div className="h-1 rounded-full bg-muted overflow-hidden">
                    <div className={`h-full ${color} transition-all`} style={{ width: `${pct}%` }} />
                </div>
            </button>
            {modalOpen && <UsageModal employee={employee} onClose={() => setModalOpen(false)} />}
        </>
    );
}

export const STATUS_CONFIG = {
    idle:          { label: "Disponible",      color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20", dot: "bg-emerald-400" },
    working:       { label: "Trabajando…",     color: "bg-blue-500/10 text-blue-400 border-blue-500/20",          dot: "bg-blue-400 animate-pulse" },
    paused:        { label: "Pausado",         color: "bg-accent text-muted-foreground border-border",              dot: "bg-accent" },
    blocked:       { label: "Requiere firma",  color: "bg-amber-500/10 text-amber-400 border-amber-500/20",        dot: "bg-amber-400 animate-pulse" },
    pending_setup: { label: "Configurando…",   color: "bg-violet-500/10 text-violet-400 border-violet-500/20",     dot: "bg-violet-400 animate-pulse" },
} as const;

export const DOMAIN_ICON: Record<string, string> = {
    billing: "💰", hr: "👥", email: "📧", crm: "🤝",
    banking: "🏦", compliance: "⚖️", excel: "📊", documents: "📄",
};

export function EmployeeCard({ employee, onToggle, onInstruct, onDelete, onAppearanceChange }: {
    employee: AIEmployee;
    onToggle: (id: string, current: AIEmployee["status"]) => void;
    onInstruct: (e: AIEmployee) => void;
    onDelete?: (id: string) => void;
    onAppearanceChange?: (id: string, icon?: string, color?: string) => void;
}) {
    const [pickerOpen, setPickerOpen] = useState(false);
    const s = STATUS_CONFIG[employee.status] ?? STATUS_CONFIG.idle;
    const icon = employee.icon || DOMAIN_ICON[employee.domain] || "🤖";
    const avatarClass = getAvatarClasses(employee.avatar_color ?? (employee.is_builtin ? "violet" : "amber"));

    return (
        <div className="bg-card border border-border rounded-xl p-4 flex flex-col gap-3 hover:border-border transition-colors">
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                    <div className="relative">
                        <div className={`w-10 h-10 rounded-full border flex items-center justify-center text-lg ${avatarClass}`}>
                            {icon}
                        </div>
                        {onAppearanceChange && (
                            <button
                                onClick={() => setPickerOpen(v => !v)}
                                className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-card border border-border flex items-center justify-center hover:bg-muted transition-colors"
                                title="Cambiar apariencia"
                            >
                                <Pencil className="w-2 h-2 text-muted-foreground" />
                            </button>
                        )}
                        {pickerOpen && onAppearanceChange && (
                            <AppearancePicker
                                currentIcon={icon}
                                currentColor={employee.avatar_color}
                                onSelect={(newIcon, newColor) => onAppearanceChange(employee.id, newIcon, newColor)}
                                onClose={() => setPickerOpen(false)}
                            />
                        )}
                    </div>
                    <div>
                        <p className="font-semibold text-foreground text-sm">{employee.name}</p>
                        <p className="text-xs text-muted-foreground">{employee.role}</p>
                    </div>
                </div>
                <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium border ${s.color}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
                    {s.label}
                </span>
            </div>
            {employee.budget_limit_usd != null && employee.budget_limit_usd > 0 && (
                <BudgetBar employee={employee} limit={employee.budget_limit_usd} />
            )}
            <div className="flex items-center justify-between pt-2 border-t border-border gap-2">
                <span className="text-[10px] text-muted-foreground capitalize">{employee.domain}</span>
                <div className="flex items-center gap-1">
                    <button onClick={() => onInstruct(employee)} disabled={employee.status === "paused"}
                        className="flex items-center gap-1 text-[10px] px-2 py-1 rounded-md border border-violet-500/30 text-violet-400 hover:bg-violet-500/10 disabled:opacity-40 transition-colors">
                        <MessageSquare className="w-3 h-3" /> Instrucción
                    </button>
                    <button onClick={() => onToggle(employee.id, employee.status)}
                        className={`text-[10px] px-2 py-1 rounded-md border transition-colors ${
                            employee.status === "paused"
                                ? "border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10"
                                : "border-border text-muted-foreground hover:bg-muted"
                        }`}>
                        {employee.status === "paused" ? "Activar" : "Pausar"}
                    </button>
                    {onDelete && (
                        <button onClick={() => onDelete(employee.id)}
                            className="text-[10px] px-2 py-1 rounded-md border border-red-500/20 text-red-400/60 hover:text-red-400 hover:bg-red-500/10 transition-colors">
                            <Trash2 className="w-3 h-3" />
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
