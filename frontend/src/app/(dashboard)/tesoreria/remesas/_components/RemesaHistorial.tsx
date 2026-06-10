"use client";

import { useCallback, useEffect, useState } from "react";
import { Download, Loader2, History } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { treasury, type Remittance } from "@/lib/api/treasury";

const fmt = (v: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(v);

const STATUS_CONFIG: Record<Remittance["status"], { label: string; cls: string; next: Remittance["status"] | null; nextLabel: string | null }> = {
    generated: { label: "Generada", cls: "text-blue-400 bg-blue-500/10 border-blue-500/20", next: "sent", nextLabel: "Marcar enviada" },
    sent: { label: "Enviada", cls: "text-amber-400 bg-amber-500/10 border-amber-500/20", next: "executed", nextLabel: "Marcar ejecutada" },
    executed: { label: "Ejecutada", cls: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20", next: "reconciled", nextLabel: "Conciliar" },
    reconciled: { label: "Conciliada", cls: "text-muted-foreground bg-muted/30 border-border", next: null, nextLabel: null },
};

const TYPE_LABEL: Record<Remittance["remittance_type"], string> = {
    "pain.001": "Transferencias",
    "pain.008": "Adeudos",
};

export default function RemesaHistorial() {
    const [items, setItems] = useState<Remittance[]>([]);
    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState<string | null>(null);

    const load = useCallback(async () => {
        try {
            const res = await treasury.remittances.list({ limit: 20 });
            setItems(res.items);
        } catch {
            // silencioso: el historial es secundario en esta vista
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { void load(); }, [load]);

    const advance = async (r: Remittance) => {
        const next = STATUS_CONFIG[r.status].next;
        if (!next) return;
        setBusy(r.id);
        try {
            await treasury.remittances.updateStatus(r.id, next);
            await load();
        } finally {
            setBusy(null);
        }
    };

    const download = async (r: Remittance) => {
        setBusy(r.id);
        try {
            await treasury.remittances.downloadXml(r.id, r.msg_id);
        } finally {
            setBusy(null);
        }
    };

    return (
        <div className="bg-card border border-border rounded-2xl p-5">
            <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
                <History className="w-4 h-4" /> Historial de remesas
            </h3>
            {loading ? (
                <div className="flex items-center gap-2 text-xs text-muted-foreground py-4">
                    <Loader2 className="w-4 h-4 animate-spin" /> Cargando…
                </div>
            ) : items.length === 0 ? (
                <p className="text-xs text-muted-foreground py-2">
                    Aún no hay remesas generadas. Las remesas SEPA que generes quedarán archivadas aquí.
                </p>
            ) : (
                <div className="space-y-2">
                    {items.map(r => {
                        const sc = STATUS_CONFIG[r.status];
                        return (
                            <div key={r.id} className="flex items-center justify-between gap-3 rounded-xl border border-border px-3 py-2">
                                <div className="min-w-0">
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs font-mono text-foreground truncate">{r.msg_id}</span>
                                        <span className={cn("text-[10px] px-2 py-0.5 rounded-full border", sc.cls)}>{sc.label}</span>
                                    </div>
                                    <p className="text-[11px] text-muted-foreground mt-0.5">
                                        {TYPE_LABEL[r.remittance_type]} · {r.nb_of_txs} {r.nb_of_txs === 1 ? "orden" : "órdenes"} · {fmt(r.total_amount)} · {r.execution_date}
                                    </p>
                                </div>
                                <div className="flex items-center gap-1 shrink-0">
                                    {sc.next && (
                                        <Button variant="ghost" size="sm" className="h-7 text-[11px]"
                                            disabled={busy === r.id} onClick={() => advance(r)}>
                                            {sc.nextLabel}
                                        </Button>
                                    )}
                                    <Button variant="ghost" size="icon" className="h-7 w-7"
                                        disabled={busy === r.id} onClick={() => download(r)} title="Descargar XML">
                                        {busy === r.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                                    </Button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
