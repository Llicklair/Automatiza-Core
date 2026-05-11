"use client";

import { useEffect, useState } from "react";
import { useNotificationSocket } from "@/lib/hooks/useNotificationSocket";
import {
    Brain, Network, Cog, Sparkles, CheckCircle2, Calculator, Users, Mail,
    Briefcase, Wallet, Scale, FolderOpen, BarChart3, Megaphone, UserPlus, User,
} from "lucide-react";

interface AgentSeen {
    domain: string;
    success: boolean;
    summary: string;
}

interface Props {
    taskId: string | null;
    active: boolean;
}

const STEPS = [
    { id: "classify",  label: "Clasificar",  icon: <Brain className="w-4 h-4" /> },
    { id: "planner",   label: "Planear",     icon: <Network className="w-4 h-4" /> },
    { id: "dispatch",  label: "Ejecutar",    icon: <Cog className="w-4 h-4" /> },
    { id: "summarize", label: "Resumir",     icon: <Sparkles className="w-4 h-4" /> },
];

const DOMAIN_META: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
    billing:     { color: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",   icon: <Calculator className="w-3 h-3" />,  label: "Billing" },
    hr:          { color: "bg-violet-500/20 text-violet-300 border-violet-500/30",      icon: <Users className="w-3 h-3" />,       label: "RRHH" },
    email:       { color: "bg-rose-500/20 text-rose-300 border-rose-500/30",            icon: <Mail className="w-3 h-3" />,        label: "Email" },
    crm:         { color: "bg-amber-500/20 text-amber-300 border-amber-500/30",         icon: <Briefcase className="w-3 h-3" />,   label: "CRM" },
    banking:     { color: "bg-sky-500/20 text-sky-300 border-sky-500/30",               icon: <Wallet className="w-3 h-3" />,      label: "Banca" },
    compliance:  { color: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",            icon: <Scale className="w-3 h-3" />,       label: "Fiscal" },
    documents:   { color: "bg-orange-500/20 text-orange-300 border-orange-500/30",      icon: <FolderOpen className="w-3 h-3" />,  label: "Docs" },
    excel:       { color: "bg-lime-500/20 text-lime-300 border-lime-500/30",            icon: <BarChart3 className="w-3 h-3" />,   label: "Excel" },
    marketing:   { color: "bg-fuchsia-500/20 text-fuchsia-300 border-fuchsia-500/30",   icon: <Megaphone className="w-3 h-3" />,   label: "Marketing" },
    recruitment: { color: "bg-teal-500/20 text-teal-300 border-teal-500/30",            icon: <UserPlus className="w-3 h-3" />,    label: "RRHH-Sel" },
    rag:         { color: "bg-indigo-500/20 text-indigo-300 border-indigo-500/30",      icon: <Brain className="w-3 h-3" />,       label: "RAG" },
    custom:      { color: "bg-slate-500/20 text-slate-300 border-slate-500/30",         icon: <User className="w-3 h-3" />,        label: "Custom" },
    summary:     { color: "bg-primary/20 text-primary border-primary/30",               icon: <Sparkles className="w-3 h-3" />,    label: "Resumen" },
};

export function TaskProgressPipeline({ taskId, active }: Props) {
    const [currentStep, setCurrentStep] = useState<string | null>(null);
    const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set());
    const [agentsSeen, setAgentsSeen] = useState<AgentSeen[]>([]);

    // Reset cuando cambia el taskId o se vuelve activo
    useEffect(() => {
        if (active && taskId) {
            setCurrentStep("classify");
            setCompletedSteps(new Set());
            setAgentsSeen([]);
        }
    }, [taskId, active]);

    useNotificationSocket({
        orchestrator_step: (msg) => {
            const msgTaskId = msg.task_id as string | undefined;
            const node = msg.node as string | undefined;
            if (!node || msgTaskId !== taskId) return;
            // Marcar este nodo como completado y avanzar
            setCompletedSteps((prev) => new Set([...prev, node]));
            // El "siguiente" lo deducimos por el orden de STEPS
            const idx = STEPS.findIndex((s) => s.id === node);
            if (idx >= 0 && idx + 1 < STEPS.length) {
                setCurrentStep(STEPS[idx + 1].id);
            } else {
                setCurrentStep(null);
            }
        },
        agent_result: (msg) => {
            const msgTaskId = msg.task_id as string | undefined;
            if (msgTaskId !== taskId) return;
            const domain = (msg.agent as string) || "unknown";
            const success = Boolean(msg.success);
            const summary = (msg.summary as string) || "";
            setAgentsSeen((prev) => {
                if (prev.some((a) => a.domain === domain && a.summary === summary)) return prev;
                return [...prev, { domain, success, summary }];
            });
        },
    });

    if (!active && agentsSeen.length === 0) return null;

    return (
        <div className="px-5 py-4 bg-gradient-to-br from-primary/5 via-transparent to-violet-500/5 border-y border-primary/10">
            {/* Pipeline horizontal */}
            <div className="relative">
                <div className="flex items-center justify-between gap-1">
                    {STEPS.map((step, i) => {
                        const isCompleted = completedSteps.has(step.id);
                        const isCurrent = currentStep === step.id && active;
                        const isPast = isCompleted && !isCurrent;
                        return (
                            <div key={step.id} className="flex items-center flex-1">
                                <div className="flex flex-col items-center flex-shrink-0 relative">
                                    {/* Nodo */}
                                    <div
                                        className={`relative w-9 h-9 rounded-full flex items-center justify-center transition-all duration-500 ${
                                            isPast
                                                ? "bg-emerald-500/20 text-emerald-300 ring-1 ring-emerald-400/50"
                                                : isCurrent
                                                    ? "bg-primary text-primary-foreground ring-2 ring-primary shadow-lg shadow-primary/50 scale-110"
                                                    : "bg-card border border-border text-muted-foreground"
                                        }`}
                                    >
                                        {isCurrent && (
                                            <>
                                                <span className="absolute inset-0 rounded-full bg-primary opacity-50 animate-ping" />
                                                <span className="absolute -inset-1 rounded-full bg-primary/30 blur-md animate-pulse" />
                                            </>
                                        )}
                                        <span className="relative z-10">
                                            {isPast ? <CheckCircle2 className="w-4 h-4" /> : step.icon}
                                        </span>
                                    </div>
                                    <span
                                        className={`text-[10px] mt-1.5 font-medium tracking-wide transition-colors ${
                                            isCurrent ? "text-primary" : isPast ? "text-emerald-300" : "text-muted-foreground"
                                        }`}
                                    >
                                        {step.label}
                                    </span>
                                </div>
                                {/* Línea conectora con flujo animado */}
                                {i < STEPS.length - 1 && (
                                    <div className="flex-1 h-0.5 mx-1 relative overflow-hidden rounded-full bg-border/60">
                                        <div
                                            className={`absolute inset-y-0 left-0 transition-all duration-700 ease-out ${
                                                completedSteps.has(step.id)
                                                    ? "w-full bg-gradient-to-r from-emerald-400 to-emerald-300"
                                                    : currentStep === step.id
                                                        ? "w-1/2 bg-gradient-to-r from-primary to-primary/40"
                                                        : "w-0 bg-transparent"
                                            }`}
                                        />
                                        {/* Pulso de luz viajando si current */}
                                        {currentStep === step.id && (
                                            <div
                                                className="absolute inset-y-0 w-8 bg-gradient-to-r from-transparent via-white/60 to-transparent blur-sm"
                                                style={{ animation: "slideRight 1.4s linear infinite" }}
                                            />
                                        )}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Chips de agentes invocados */}
            {agentsSeen.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                    {agentsSeen.map((a, i) => {
                        const meta = DOMAIN_META[a.domain] ?? DOMAIN_META.custom;
                        return (
                            <span
                                key={`${a.domain}-${i}`}
                                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[10px] ${meta.color} ${a.success ? "" : "opacity-60 line-through"} animate-in slide-in-from-bottom-1 fade-in duration-300`}
                            >
                                {meta.icon}
                                <span className="font-medium">{meta.label}</span>
                            </span>
                        );
                    })}
                </div>
            )}

            <style jsx global>{`
                @keyframes slideRight {
                    0% { left: -32px; }
                    100% { left: 100%; }
                }
            `}</style>
        </div>
    );
}
