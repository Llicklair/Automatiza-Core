"use client";

import { X } from "lucide-react";
import { Node } from "reactflow";

const DOMAIN_OPTIONS = [
    { value: "billing",    label: "Facturación" },
    { value: "hr",         label: "RRHH / Nóminas" },
    { value: "crm",        label: "CRM / Clientes" },
    { value: "email",      label: "Email" },
    { value: "documents",  label: "Documentos" },
    { value: "banking",    label: "Banca" },
    { value: "compliance", label: "Fiscal / Compliance" },
    { value: "excel",      label: "Excel / Informes" },
    { value: "rag",        label: "Búsqueda documental" },
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
                            <option key={d.value} value={d.value}>{d.label}</option>
                        ))}
                    </select>
                </div>
            )}

            {/* Instruction (skill/action) */}
            {(type === "skill" || type === "action") && (
                <div>
                    <label className="block text-[10px] text-zinc-500 uppercase tracking-wider mb-1">
                        Instrucción <span className="text-indigo-400 normal-case">(lo que hará el agente)</span>
                    </label>
                    <textarea
                        value={data?.instruction || data?.description || ""}
                        onChange={e => update("instruction", e.target.value)}
                        rows={3}
                        placeholder="Ej: Genera una factura de 100€ para el cliente ACME S.L. por servicios de consultoría"
                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-3 py-2 text-white text-xs focus:outline-none focus:border-indigo-500 resize-none"
                    />
                    <p className="text-[9px] text-zinc-600 mt-1">Escribe en lenguaje natural. Cuanto más específico, mejor resultado.</p>
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
