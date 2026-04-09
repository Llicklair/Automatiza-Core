"use client";

import { Bot, GitBranch, Clock, ShieldCheck, GitFork } from "lucide-react";

interface WorkflowToolbarProps {
    onAddNode: (type: "skill" | "conditional" | "delay" | "approval_gate") => void;
    onAddParallelBranch: () => void;
}

const NODE_TYPES = [
    { type: "skill" as const, label: "Agente IA", icon: Bot, color: "emerald" },
    { type: "conditional" as const, label: "Condicional", icon: GitBranch, color: "amber" },
    { type: "delay" as const, label: "Espera", icon: Clock, color: "blue" },
    { type: "approval_gate" as const, label: "Aprobación", icon: ShieldCheck, color: "orange" },
];

const COLOR_MAP: Record<string, string> = {
    emerald: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30 hover:bg-emerald-500/20",
    amber: "text-amber-400 bg-amber-500/10 border-amber-500/30 hover:bg-amber-500/20",
    blue: "text-blue-400 bg-blue-500/10 border-blue-500/30 hover:bg-blue-500/20",
    orange: "text-orange-400 bg-orange-500/10 border-orange-500/30 hover:bg-orange-500/20",
};

export default function WorkflowToolbar({ onAddNode, onAddParallelBranch }: WorkflowToolbarProps) {
    return (
        <div className="flex flex-wrap items-center gap-2 px-3 py-2 bg-card border border-border rounded-xl backdrop-blur-sm">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mr-1">Añadir:</span>
            {NODE_TYPES.map(({ type, label, icon: Icon, color }) => (
                <button
                    key={type}
                    type="button"
                    onClick={() => onAddNode(type)}
                    className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-medium transition-colors ${COLOR_MAP[color]}`}
                    title={`Añadir nodo ${label}`}
                >
                    <Icon className="w-3.5 h-3.5" />
                    {label}
                </button>
            ))}
            <button
                type="button"
                onClick={onAddParallelBranch}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-medium transition-colors text-violet-400 bg-violet-500/10 border-violet-500/30 hover:bg-violet-500/20"
                title="Añadir dos nodos en paralelo conectados al último nodo"
            >
                <GitFork className="w-3.5 h-3.5" />
                Rama paralela
            </button>
        </div>
    );
}
