"use client";

import { useEffect, useState } from "react";
import { api, type Approval } from "@/lib/api";
import { CheckCircle2, XCircle, Clock, ShieldCheck, ChevronDown, X, Trash2 } from "lucide-react";
import { useToastStore } from "@/stores/toast";

const RISK_STYLE: Record<string, string> = {
    low: "text-zinc-300 bg-zinc-700/50 border-zinc-600",
    medium: "text-amber-300 bg-amber-500/10 border-amber-500/30",
    high: "text-red-300 bg-red-500/10 border-red-500/30",
    critical: "text-red-200 bg-red-700/20 border-red-600/40",
};
const RISK_LABEL: Record<string, string> = {
    low: "Bajo", medium: "Medio", high: "Alto", critical: "Crítico",
};

const minutesUntil = (iso: string) => {
    const diff = new Date(iso).getTime() - Date.now();
    return Math.max(0, Math.floor(diff / 60000));
};

function ApprovalCard({
    approval: a,
    deciding,
    onApprove,
    onRejectClick,
}: {
    approval: Approval;
    deciding: string | null;
    onApprove: (id: string) => void;
    onRejectClick: (id: string) => void;
}) {
    const [open, setOpen] = useState(false);
    const mins = minutesUntil(a.expires_at);
    const urgent = mins < 15;

    return (
        <div
            className={`rounded-xl border p-6 transition duration-300 ${urgent ? "border-amber-500/40 bg-amber-500/5" : "border-[#27272a] bg-[#111113]"
                }`}
        >
            <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                    <p className="text-white font-medium">{a.action_description}</p>

                    <div className="flex items-center gap-3 mt-3">
                        <span className={`text-xs px-2.5 py-1 rounded-full border font-medium ${RISK_STYLE[a.risk_level] ?? RISK_STYLE.low}`}>
                            Riesgo {RISK_LABEL[a.risk_level] ?? a.risk_level}
                        </span>
                        <span className={`flex items-center gap-1 text-xs ${urgent ? "text-amber-400" : "text-zinc-500"}`}>
                            <Clock className="w-3.5 h-3.5" />
                            {mins > 0 ? `Expira en ${mins} min` : "Expirada"}
                        </span>
                    </div>

                    {Boolean(a.action_payload) && (
                        <div className="mt-4">
                            <button
                                onClick={() => setOpen(!open)}
                                className="flex items-center gap-2 text-xs text-zinc-400 hover:text-zinc-300 transition-colors select-none"
                            >
                                <span>Ver detalles de la acción</span>
                                <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-300 ${open ? "rotate-180" : ""}`} />
                            </button>
                            <div
                                className={`grid transition-[grid-template-rows,opacity,margin] duration-300 ease-in-out ${open ? "grid-rows-[1fr] opacity-100 mt-3" : "grid-rows-[0fr] opacity-0 mt-0"
                                    }`}
                            >
                                <div className="overflow-hidden">
                                    <pre className="px-4 py-3 rounded-lg bg-[#0d0d0f] text-xs text-zinc-300 border border-[#27272a] overflow-x-auto">
                                        {JSON.stringify(a.action_payload, null, 2)}
                                    </pre>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                <div className="flex gap-2 flex-shrink-0">
                    <button
                        onClick={() => onRejectClick(a.id)}
                        disabled={deciding === a.id || mins === 0}
                        className="flex items-center gap-1.5 px-4 py-2 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 disabled:opacity-40 text-sm transition"
                    >
                        <XCircle className="w-4 h-4" /> Rechazar
                    </button>
                    <button
                        onClick={() => onApprove(a.id)}
                        disabled={deciding === a.id || mins === 0}
                        className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white text-sm transition shadow-[0_0_15px_rgba(16,185,129,0.2)] hover:shadow-[0_0_20px_rgba(16,185,129,0.3)]"
                    >
                        <CheckCircle className="w-4 h-4" /> Aprobar
                    </button>
                </div>
            </div>
        </div>
    );
}

// Helper para evitar error de importación si CheckCircle2 no funciona bien a veces
const CheckCircle = CheckCircle2;

export default function AprobacionesPage() {
    const toast = useToastStore();
    const [approvals, setApprovals] = useState<Approval[]>([]);
    const [loading, setLoading] = useState(true);
    const [deciding, setDeciding] = useState<string | null>(null);
    const [cleaning, setCleaning] = useState(false);

    // Estado del Modal de Rechazo
    const [rejectingId, setRejectingId] = useState<string | null>(null);
    const [rejectionReason, setRejectionReason] = useState("");

    const load = () => {
        api.approvals.list()
            .then(setApprovals)
            .catch(() => { })
            .finally(() => setLoading(false));
    };

    useEffect(() => { load(); }, []);

    async function handleApprove(id: string) {
        setDeciding(id);
        try {
            await api.approvals.decide(id, true);
            load();
        } catch (err: unknown) {
            toast.error(err instanceof Error ? err.message : "Error al procesar la decisión");
        } finally {
            setDeciding(null);
        }
    }

    async function handleConfirmReject() {
        if (!rejectingId) return;
        const id = rejectingId;
        const reason = rejectionReason.trim() || undefined;

        setRejectingId(null);
        setRejectionReason("");
        setDeciding(id);

        try {
            await api.approvals.decide(id, false, reason);
            load();
        } catch (err: unknown) {
            toast.error(err instanceof Error ? err.message : "Error al procesar el rechazo");
        } finally {
            setDeciding(null);
        }
    }

    async function handleCleanup() {
        if (!confirm("¿Eliminar todas las aprobaciones expiradas y ya resueltas?")) return;
        setCleaning(true);
        try {
            await api.approvals.cleanup();
            load();
        } catch {
            toast.error("Error al limpiar aprobaciones");
        } finally {
            setCleaning(false);
        }
    }

    return (
        <div className="p-8 max-w-4xl mx-auto relative">
            <div className="flex items-start justify-between mb-8">
                <div>
                    <h1 className="text-2xl font-bold text-white">Aprobaciones pendientes</h1>
                    <p className="text-sm text-zinc-400 mt-1">
                        Revisa y aprueba o rechaza las acciones propuestas por los agentes
                    </p>
                </div>
                <button
                    onClick={handleCleanup}
                    disabled={cleaning || loading}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-red-500/20 text-red-400/70 hover:text-red-400 hover:bg-red-500/10 text-xs font-medium transition disabled:opacity-40"
                    title="Eliminar aprobaciones expiradas y resueltas"
                >
                    {cleaning ? <XCircle className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                    Limpiar historial
                </button>
            </div>

            {loading ? (
                <div className="text-center py-20 text-zinc-500 text-sm">Cargando…</div>
            ) : approvals.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-24 text-center bg-[#111113] border border-[#27272a] rounded-xl">
                    <ShieldCheck className="w-12 h-12 text-emerald-500/40 mb-3" />
                    <p className="text-white font-medium">Sin aprobaciones pendientes</p>
                    <p className="text-sm text-zinc-500 mt-1">Los agentes no requieren tu atención ahora mismo</p>
                </div>
            ) : (
                <div className="space-y-4">
                    {approvals.map(a => (
                        <ApprovalCard
                            key={a.id}
                            approval={a}
                            deciding={deciding}
                            onApprove={handleApprove}
                            onRejectClick={(id) => {
                                setRejectingId(id);
                                setRejectionReason("");
                            }}
                        />
                    ))}
                </div>
            )}

            {/* Modal de Rechazo */}
            {rejectingId && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                    {/* Backdrop */}
                    <div
                        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                        onClick={() => setRejectingId(null)}
                    />

                    {/* Modal Box */}
                    <div className="relative w-full max-w-md bg-[#18181b] border border-[#27272a] rounded-2xl shadow-2xl p-6">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-bold text-white flex items-center gap-2">
                                <XCircle className="w-5 h-5 text-red-500" />
                                Rechazar Acción
                            </h3>
                            <button
                                onClick={() => setRejectingId(null)}
                                className="text-zinc-500 hover:text-white transition-colors"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <p className="text-sm text-zinc-400 mb-4">
                            Estás a punto de rechazar esta acción. Puedes indicar un motivo opcional para que el agente lo tenga en cuenta en futuros intentos.
                        </p>

                        <div className="mb-6">
                            <label className="block text-xs font-medium text-zinc-500 uppercase tracking-wide mb-2">
                                Motivo del rechazo (opcional)
                            </label>
                            <textarea
                                value={rejectionReason}
                                onChange={(e) => setRejectionReason(e.target.value)}
                                placeholder="Ej: Faltan datos en el documento..."
                                className="w-full bg-black/40 border border-[#27272a] rounded-xl p-3 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:border-red-500/50 focus:ring-1 focus:ring-red-500/50 transition-all resize-none h-24"
                                autoFocus
                            />
                        </div>

                        <div className="flex gap-3 justify-end">
                            <button
                                onClick={() => setRejectingId(null)}
                                className="px-4 py-2 rounded-lg text-sm font-medium text-zinc-400 hover:text-white hover:bg-white/5 transition-colors"
                            >
                                Cancelar
                            </button>
                            <button
                                onClick={handleConfirmReject}
                                className="px-5 py-2 rounded-xl text-sm font-medium bg-red-600 hover:bg-red-500 text-white transition-all shadow-[0_0_15px_rgba(220,38,38,0.2)] hover:shadow-[0_0_20px_rgba(220,38,38,0.3)]"
                            >
                                Confirmar Rechazo
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
