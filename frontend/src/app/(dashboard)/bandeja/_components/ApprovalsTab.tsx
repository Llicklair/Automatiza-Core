"use client";

import { useEffect, useState } from "react";
import { api, type Approval } from "@/lib/api";
import { XCircle, ShieldCheck, Trash2, X } from "lucide-react";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { ApprovalCard } from "./ApprovalCard";

interface ApprovalsTabProps {
    onPendingCount: (count: number) => void;
}

export function ApprovalsTab({ onPendingCount }: ApprovalsTabProps) {
    const toast = useToastStore();
    const [approvals, setApprovals] = useState<Approval[]>([]);
    const [loading, setLoading] = useState(true);
    const [deciding, setDeciding] = useState<string | null>(null);
    const [cleaning, setCleaning] = useState(false);

    // Rejection modal state
    const [rejectingId, setRejectingId] = useState<string | null>(null);
    const [rejectionReason, setRejectionReason] = useState("");

    const load = () => {
        api.approvals.list()
            .then(setApprovals)
            .catch(() => { })
            .finally(() => setLoading(false));
    };

    useEffect(() => { load(); }, []);

    // Polling every 10s
    useEffect(() => {
        const interval = setInterval(() => {
            api.approvals.list().then(setApprovals).catch(() => { });
        }, 10_000);
        return () => clearInterval(interval);
    }, []);

    // Report pending count to parent
    useEffect(() => {
        const pending = approvals.filter(a => {
            const diff = new Date(a.expires_at).getTime() - Date.now();
            return diff > 0;
        }).length;
        onPendingCount(pending);
    }, [approvals, onPendingCount]);

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
        if (!await showConfirm({ message: "¿Eliminar todas las aprobaciones expiradas y ya resueltas?", confirmLabel: "Eliminar", confirmVariant: "danger" })) return;
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
        <div className="relative">
            {/* Cleanup button */}
            <div className="flex justify-end mb-4">
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
                <div className="text-center py-20 text-muted-foreground text-sm">Cargando…</div>
            ) : approvals.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-24 text-center bg-card border border-border rounded-xl">
                    <ShieldCheck className="w-12 h-12 text-emerald-500/40 mb-3" />
                    <p className="text-foreground font-medium">Sin aprobaciones pendientes</p>
                    <p className="text-sm text-muted-foreground mt-1">Los agentes no requieren tu atención ahora mismo</p>
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

            {/* Rejection Modal */}
            {rejectingId && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                    {/* Backdrop */}
                    <div
                        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                        onClick={() => setRejectingId(null)}
                    />

                    {/* Modal Box */}
                    <div className="relative w-full max-w-md bg-card border border-border rounded-2xl shadow-2xl p-6">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
                                <XCircle className="w-5 h-5 text-red-500" />
                                Rechazar Acción
                            </h3>
                            <button
                                onClick={() => setRejectingId(null)}
                                className="text-muted-foreground hover:text-foreground transition-colors"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <p className="text-sm text-muted-foreground mb-4">
                            Estás a punto de rechazar esta acción. Puedes indicar un motivo opcional para que el agente lo tenga en cuenta en futuros intentos.
                        </p>

                        <div className="mb-6">
                            <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
                                Motivo del rechazo (opcional)
                            </label>
                            <textarea
                                value={rejectionReason}
                                onChange={(e) => setRejectionReason(e.target.value)}
                                placeholder="Ej: Faltan datos en el documento..."
                                className="w-full bg-muted border border-border rounded-xl p-3 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:border-red-500/50 focus:ring-1 focus:ring-red-500/50 transition-all resize-none h-24"
                                autoFocus
                            />
                        </div>

                        <div className="flex gap-3 justify-end">
                            <button
                                onClick={() => setRejectingId(null)}
                                className="px-4 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-accent/50 transition-colors"
                            >
                                Cancelar
                            </button>
                            <button
                                onClick={handleConfirmReject}
                                className="px-5 py-2 rounded-xl text-sm font-medium bg-red-600 hover:bg-red-500 text-foreground transition-all shadow-[0_0_15px_rgba(220,38,38,0.2)] hover:shadow-[0_0_20px_rgba(220,38,38,0.3)]"
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
