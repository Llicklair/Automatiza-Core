"use client";

import { Banknote, CreditCard, Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
    open: boolean;
    onClose: () => void;
    total: number;
    busy: boolean;
    onPay: (method: "cash" | "card") => void;
}

const fmt = (n: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(n);

export function PaymentModal({ open, onClose, total, busy, onPay }: Props) {
    if (!open) return null;
    return (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-card border border-border rounded-2xl w-full max-w-md overflow-hidden">
                <div className="p-4 flex items-center justify-between border-b border-border">
                    <h3 className="text-sm font-medium text-foreground">Cobrar</h3>
                    <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onClose} disabled={busy} aria-label="Cerrar">
                        <X className="w-4 h-4" aria-hidden="true" />
                    </Button>
                </div>
                <div className="p-6 space-y-5">
                    <div className="text-center">
                        <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">A cobrar</p>
                        <p className="text-4xl font-bold text-foreground tabular-nums">{fmt(total)}</p>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                        <button
                            onClick={() => onPay("cash")}
                            disabled={busy}
                            className="flex flex-col items-center gap-2 p-5 rounded-xl border border-border bg-background hover:bg-muted hover:border-emerald-500/50 disabled:opacity-50 transition-colors"
                        >
                            <Banknote className="w-7 h-7 text-emerald-400" />
                            <span className="text-sm font-medium text-foreground">Efectivo</span>
                        </button>
                        <button
                            onClick={() => onPay("card")}
                            disabled={busy}
                            className="flex flex-col items-center gap-2 p-5 rounded-xl border border-border bg-background hover:bg-muted hover:border-sky-500/50 disabled:opacity-50 transition-colors"
                        >
                            <CreditCard className="w-7 h-7 text-sky-400" />
                            <span className="text-sm font-medium text-foreground">Tarjeta</span>
                        </button>
                    </div>
                    {busy && (
                        <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
                            <Loader2 className="w-3.5 h-3.5 animate-spin" /> Procesando cobro…
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
