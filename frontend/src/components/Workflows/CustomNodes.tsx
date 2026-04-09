"use client";

import { memo } from "react";
import { Handle, Position, NodeProps } from "reactflow";
import {
    Zap, FileText, GitBranch, Clock, ShieldCheck,
    Receipt, Users, Mail, BarChart3, Database, Bot
} from "lucide-react";

// Domain icon mapping
const DOMAIN_ICONS: Record<string, React.ElementType> = {
    billing: Receipt,
    hr: Users,
    email: Mail,
    crm: BarChart3,
    documents: FileText,
    banking: Database,
    compliance: ShieldCheck,
};

function getDomainIcon(domain?: string) {
    if (!domain) return Bot;
    return DOMAIN_ICONS[domain] || Bot;
}

// ── Trigger Node ──────────────────────────────────────────────────────────────
export const TriggerNode = memo(({ data }: NodeProps) => {
    const triggerType = data?.trigger_type || "manual";
    const sublabel = triggerType === "event_based" ? "Evento" : triggerType === "schedule_based" ? "Programado" : "Manual";
    return (
        <div className="bg-card border-2 border-indigo-500 rounded-xl px-4 py-3 min-w-[180px] shadow-lg shadow-indigo-500/10">
            <Handle type="source" position={Position.Bottom} className="!bg-indigo-500 !w-3 !h-3 !border-2 !border-indigo-300" />
            <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-indigo-500/20 flex items-center justify-center">
                    <Zap className="w-4 h-4 text-indigo-400" />
                </div>
                <div className="min-w-0">
                    <p className="text-[10px] uppercase tracking-wider text-indigo-400 font-semibold">Trigger</p>
                    <p className="text-xs text-foreground font-medium truncate">{data?.label || sublabel}</p>
                </div>
            </div>
        </div>
    );
});
TriggerNode.displayName = "TriggerNode";

// ── Skill Node ────────────────────────────────────────────────────────────────
export const SkillNode = memo(({ data }: NodeProps) => {
    const domain = data?.domain || "billing";
    const Icon = getDomainIcon(domain);
    return (
        <div className="bg-card border-2 border-emerald-500 rounded-xl px-4 py-3 min-w-[180px] shadow-lg shadow-emerald-500/10">
            <Handle type="target" position={Position.Top} className="!bg-emerald-500 !w-3 !h-3 !border-2 !border-emerald-300" />
            <Handle type="source" position={Position.Bottom} className="!bg-emerald-500 !w-3 !h-3 !border-2 !border-emerald-300" />
            <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center">
                    <Icon className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="min-w-0 flex-1">
                    <p className="text-[10px] uppercase tracking-wider text-emerald-400 font-semibold">{domain}</p>
                    <p className="text-xs text-foreground font-medium truncate max-w-[140px]">{data?.label || "Ejecutar agente"}</p>
                </div>
            </div>
        </div>
    );
});
SkillNode.displayName = "SkillNode";

// ── Conditional Node ──────────────────────────────────────────────────────────
export const ConditionalNode = memo(({ data }: NodeProps) => {
    const field = data?.condition?.field || "condición";
    return (
        <div className="bg-card border-2 border-amber-500 rounded-xl px-4 py-3 min-w-[180px] shadow-lg shadow-amber-500/10">
            <Handle type="target" position={Position.Top} className="!bg-amber-500 !w-3 !h-3 !border-2 !border-amber-300" />
            <Handle type="source" position={Position.Bottom} id="true" className="!bg-emerald-500 !w-3 !h-3 !border-2 !border-emerald-300 !left-[30%]" />
            <Handle type="source" position={Position.Bottom} id="false" className="!bg-red-500 !w-3 !h-3 !border-2 !border-red-300 !left-[70%]" />
            <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-amber-500/20 flex items-center justify-center">
                    <GitBranch className="w-4 h-4 text-amber-400" />
                </div>
                <div className="min-w-0 flex-1">
                    <p className="text-[10px] uppercase tracking-wider text-amber-400 font-semibold">Condicional</p>
                    <p className="text-xs text-foreground font-medium truncate max-w-[140px]">{data?.label || field}</p>
                </div>
            </div>
            <div className="flex justify-between mt-2 px-1 text-[9px] font-semibold">
                <span className="text-emerald-400">Sí</span>
                <span className="text-red-400">No</span>
            </div>
        </div>
    );
});
ConditionalNode.displayName = "ConditionalNode";

// ── Delay Node ────────────────────────────────────────────────────────────────
export const DelayNode = memo(({ data }: NodeProps) => {
    const seconds = data?.delay_seconds || 0;
    const label = seconds >= 3600 ? `${Math.round(seconds / 3600)}h` : seconds >= 60 ? `${Math.round(seconds / 60)}min` : `${seconds}s`;
    return (
        <div className="bg-card border-2 border-blue-500 rounded-xl px-4 py-3 min-w-[180px] shadow-lg shadow-blue-500/10">
            <Handle type="target" position={Position.Top} className="!bg-blue-500 !w-3 !h-3 !border-2 !border-blue-300" />
            <Handle type="source" position={Position.Bottom} className="!bg-blue-500 !w-3 !h-3 !border-2 !border-blue-300" />
            <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
                    <Clock className="w-4 h-4 text-blue-400" />
                </div>
                <div className="min-w-0">
                    <p className="text-[10px] uppercase tracking-wider text-blue-400 font-semibold">Espera</p>
                    <p className="text-xs text-foreground font-medium">{data?.label || `Delay ${label}`}</p>
                </div>
            </div>
        </div>
    );
});
DelayNode.displayName = "DelayNode";

// ── Approval Gate Node ────────────────────────────────────────────────────────
export const ApprovalGateNode = memo(({ data }: NodeProps) => {
    return (
        <div className="bg-card border-2 border-orange-500 rounded-xl px-4 py-3 min-w-[180px] shadow-lg shadow-orange-500/10">
            <Handle type="target" position={Position.Top} className="!bg-orange-500 !w-3 !h-3 !border-2 !border-orange-300" />
            <Handle type="source" position={Position.Bottom} className="!bg-orange-500 !w-3 !h-3 !border-2 !border-orange-300" />
            <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-orange-500/20 flex items-center justify-center">
                    <ShieldCheck className="w-4 h-4 text-orange-400" />
                </div>
                <div className="min-w-0">
                    <p className="text-[10px] uppercase tracking-wider text-orange-400 font-semibold">Aprobación</p>
                    <p className="text-xs text-foreground font-medium truncate max-w-[140px]">{data?.label || "Requiere aprobación"}</p>
                </div>
            </div>
        </div>
    );
});
ApprovalGateNode.displayName = "ApprovalGateNode";

// ── Action Node (legacy / generic) ───────────────────────────────────────────
export const ActionNode = memo(({ data }: NodeProps) => {
    const domain = data?.domain || "billing";
    const Icon = getDomainIcon(domain);
    return (
        <div className="bg-card border-2 border-emerald-500 rounded-xl px-4 py-3 min-w-[180px] shadow-lg shadow-emerald-500/10">
            <Handle type="target" position={Position.Top} className="!bg-emerald-500 !w-3 !h-3 !border-2 !border-emerald-300" />
            <Handle type="source" position={Position.Bottom} className="!bg-emerald-500 !w-3 !h-3 !border-2 !border-emerald-300" />
            <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center">
                    <Icon className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="min-w-0 flex-1">
                    <p className="text-[10px] uppercase tracking-wider text-emerald-400 font-semibold">{domain}</p>
                    <p className="text-xs text-foreground font-medium truncate max-w-[140px]">{data?.label || "Acción"}</p>
                </div>
            </div>
        </div>
    );
});
ActionNode.displayName = "ActionNode";

// ── Node type registry for ReactFlow ─────────────────────────────────────────
export const customNodeTypes = {
    trigger: TriggerNode,
    skill: SkillNode,
    action: ActionNode,
    conditional: ConditionalNode,
    delay: DelayNode,
    approval_gate: ApprovalGateNode,
};
