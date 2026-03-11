"use client";

import { X } from "lucide-react";
import { Node } from "reactflow";

const DOMAIN_OPTIONS = [
    "billing", "hr", "email", "crm", "documents", "banking", "compliance", "excel", "rag",
];

interface NodeConfigPanelProps {
    node: Node;
    onUpdate: (id: string, data: Record<string, any>) => void;
    onDelete: (id: string) => void;
    onClose: () => void;
}

export default function NodeConfigPanel({ node, onUpdate, onDelete, onClose }: NodeConfigPanelProps) {
    const { data, type } = node;

    const update = (key: string, value: any) => {
        onUpdate(node.id, { ...data, [key]: value });
    };

    return (
        <div className="w-72 bg-[#111113] border border-zinc-800 rounded-xl p-4 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-white">Configurar nodo</h3>
                <button onClick={onClose} className="text-zinc-400 hover:text-white transition">
                    <X className="w-4 h-4" />
                </button>
            </div>

            {/* Label */}
            <div>
                <label className="block text-[10px] text-zinc-500 uppercase tracking-wider mb-1">Etiqueta</label>
                <input
                    type="text"
                    value={data?.label || ""}
                    onChange={e => update("label", e.target.value)}
                    className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-3 py-2 text-white text-xs focus:outline-none focus:border-indigo-500 transition"
                />
            </div>

            {/* Type display */}
            <div>
                <label className="block text-[10px] text-zinc-500 uppercase tracking-wider mb-1">Tipo</label>
                <span className="text-xs text-zinc-300 capitalize">{type === "approval_gate" ? "Aprobación" : type === "skill" ? "Agente IA" : type === "conditional" ? "Condicional" : type === "delay" ? "Espera" : type}</span>
            </div>

            {/* Domain (skill/action nodes) */}
            {(type === "skill" || type === "action") && (
                <div>
                    <label className="block text-[10px] text-zinc-500 uppercase tracking-wider mb-1">Dominio del agente</label>
                    <select
                        value={data?.domain || "billing"}
                        onChange={e => update("domain", e.target.value)}
                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-3 py-2 text-white text-xs focus:outline-none focus:border-indigo-500"
                    >
                        {DOMAIN_OPTIONS.map(d => (
                            <option key={d} value={d}>{d}</option>
                        ))}
                    </select>
                </div>
            )}

            {/* Instruction (skill/action) */}
            {(type === "skill" || type === "action") && (
                <div>
                    <label className="block text-[10px] text-zinc-500 uppercase tracking-wider mb-1">Instrucción</label>
                    <textarea
                        value={data?.description || ""}
                        onChange={e => update("description", e.target.value)}
                        rows={3}
                        placeholder="Ej: Generar informe de ventas del mes"
                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-3 py-2 text-white text-xs focus:outline-none focus:border-indigo-500 resize-none"
                    />
                </div>
            )}

            {/* Delay seconds */}
            {type === "delay" && (
                <div>
                    <label className="block text-[10px] text-zinc-500 uppercase tracking-wider mb-1">Segundos de espera</label>
                    <input
                        type="number"
                        min={0}
                        value={data?.delay_seconds || 0}
                        onChange={e => update("delay_seconds", parseInt(e.target.value) || 0)}
                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-3 py-2 text-white text-xs focus:outline-none focus:border-indigo-500"
                    />
                </div>
            )}

            {/* Condition (conditional) */}
            {type === "conditional" && (
                <div>
                    <label className="block text-[10px] text-zinc-500 uppercase tracking-wider mb-1">Condición</label>
                    <input
                        type="text"
                        value={data?.condition?.field || ""}
                        onChange={e => update("condition", { ...data?.condition, field: e.target.value })}
                        placeholder="Ej: invoice.amount > 1000"
                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-3 py-2 text-white text-xs focus:outline-none focus:border-indigo-500"
                    />
                </div>
            )}

            {/* Approval gate */}
            {type === "approval_gate" && (
                <div>
                    <label className="block text-[10px] text-zinc-500 uppercase tracking-wider mb-1">Mensaje de aprobación</label>
                    <input
                        type="text"
                        value={data?.description || ""}
                        onChange={e => update("description", e.target.value)}
                        placeholder="Ej: Aprobar envío de nóminas"
                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-3 py-2 text-white text-xs focus:outline-none focus:border-indigo-500"
                    />
                </div>
            )}

            <button
                type="button"
                onClick={() => onDelete(node.id)}
                className="w-full text-xs text-red-400 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 rounded-lg py-2 font-medium transition-colors"
            >
                Eliminar nodo
            </button>
        </div>
    );
}
