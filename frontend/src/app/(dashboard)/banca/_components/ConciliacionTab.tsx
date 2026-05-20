"use client";

import { useCallback, useEffect, useState } from "react";
import {
    ArrowDownLeft, ArrowUpRight, Check, CheckCircle2,
    EyeOff, Loader2, RefreshCw, Sparkles, Undo2, X,
} from "lucide-react";
import { api } from "@/lib/api";
import type { BankTransaction, Invoice, ReconciliationSuggestion } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { KpiCard } from "@/components/shared/KpiCard";
import { useToastStore } from "@/stores/toast";

const fmt = (n: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(n);
const fmtDate = (d: string) =>
    new Date(d).toLocaleDateString("es-ES", { day: "2-digit", month: "short" });

export function ConciliacionTab() {
    const toast = useToastStore();
    const [suggestions, setSuggestions] = useState<ReconciliationSuggestion[]>([]);
    const [reconciled, setReconciled] = useState<BankTransaction[]>([]);
    const [ignored, setIgnored] = useState<BankTransaction[]>([]);
    const [allInvoices, setAllInvoices] = useState<Invoice[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isAutoMatching, setIsAutoMatching] = useState(false);
    const [actionId, setActionId] = useState<string | null>(null);
    // Per-row selected invoice for manual reconciliation
    const [selectedInvoice, setSelectedInvoice] = useState<Record<string, string>>({});

    const load = useCallback(async () => {
        setIsLoading(true);
        try {
            const [suggs, txAll, invAll] = await Promise.all([
                api.banking.reconciliation.suggestions(),
                api.banking.transactions.list(),
                api.erp.invoices.list(),
            ]);
            setSuggestions(suggs);
            setReconciled(txAll.filter((t) => t.status === "reconciled"));
            setIgnored(txAll.filter((t) => t.status === "ignored"));
            setAllInvoices(invAll.filter((i) => i.status !== "paid"));
        } catch {
            toast.error("Error al cargar datos de conciliación");
        } finally {
            setIsLoading(false);
        }
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { load(); }, [load]);

    const handleAutoMatch = async () => {
        setIsAutoMatching(true);
        try {
            const res = await api.banking.reconciliation.autoMatch();
            if (res.matched > 0) {
                toast.success(`Auto-conciliadas ${res.matched} transacciones`);
                await load();
            } else {
                toast.info("No se encontraron coincidencias automáticas");
            }
        } catch {
            toast.error("Error en auto-conciliación");
        } finally {
            setIsAutoMatching(false);
        }
    };

    const handleReconcile = async (txId: string, invoiceId: string) => {
        setActionId(txId);
        try {
            await api.banking.transactions.reconcile(txId, invoiceId);
            await load();
        } catch (e: any) {
            toast.error(e?.message ?? "Error al conciliar");
        } finally {
            setActionId(null);
        }
    };

    const handleIgnore = async (txId: string) => {
        setActionId(txId);
        try {
            await api.banking.transactions.ignore(txId);
            await load();
        } catch {
            toast.error("Error al ignorar");
        } finally {
            setActionId(null);
        }
    };

    const handleUnreconcile = async (txId: string) => {
        setActionId(txId);
        try {
            await api.banking.transactions.unreconcile(txId);
            await load();
        } catch {
            toast.error("Error al deshacer");
        } finally {
            setActionId(null);
        }
    };

    const pendingAmount = suggestions.reduce((s, r) => s + Math.abs(r.tx.amount), 0);

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-48 text-muted-foreground text-sm gap-2">
                <Loader2 className="w-4 h-4 animate-spin" /> Cargando conciliación…
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* KPIs */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KpiCard title="Pendientes" value={suggestions.length} icon={RefreshCw} />
                <KpiCard title="Importe pendiente" value={fmt(pendingAmount)} icon={RefreshCw} />
                <KpiCard title="Conciliadas" value={reconciled.length} icon={CheckCircle2} />
                <KpiCard title="Ignoradas" value={ignored.length} icon={EyeOff} />
            </div>

            {/* Auto-match */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-sm font-semibold text-foreground">
                        Transacciones pendientes ({suggestions.length})
                    </h2>
                    <p className="text-xs text-muted-foreground">
                        Las sugerencias se calculan por coincidencia de importe (±0,02€).
                    </p>
                </div>
                <Button
                    size="sm"
                    onClick={handleAutoMatch}
                    disabled={isAutoMatching || suggestions.length === 0}
                >
                    {isAutoMatching
                        ? <><Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />Procesando…</>
                        : <><Sparkles className="mr-2 h-3.5 w-3.5" />Auto-conciliar</>}
                </Button>
            </div>

            {/* Pending list */}
            {suggestions.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-32 gap-2 text-muted-foreground rounded-xl border border-border bg-card">
                    <CheckCircle2 className="w-6 h-6 opacity-40 text-emerald-400" />
                    <p className="text-sm">Todo conciliado</p>
                </div>
            ) : (
                <div className="space-y-2">
                    {suggestions.map(({ tx, suggestions: suggs }) => {
                        const busy = actionId === tx.id;
                        const sel = selectedInvoice[tx.id] ?? (suggs[0]?.id ?? "");
                        const invoicePool = suggs.length > 0 ? suggs : allInvoices.map((i) => ({
                            id: i.id,
                            invoice_number: i.invoice_number ?? null,
                            amount_total: i.amount_total,
                            client_name: i.client?.name ?? null,
                            status: i.status,
                            date: i.date ?? null,
                        }));

                        return (
                            <div
                                key={tx.id}
                                className="grid grid-cols-1 md:grid-cols-[1fr_auto] items-center gap-4 rounded-xl border border-border bg-card px-4 py-3"
                            >
                                {/* Left: tx info + invoice selector */}
                                <div className="flex flex-wrap items-center gap-4">
                                    <div className="min-w-[80px]">
                                        <p className="text-xs text-muted-foreground font-mono">{fmtDate(tx.date)}</p>
                                        <p className={`text-base font-bold tabular-nums flex items-center gap-1 ${tx.amount >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                                            {tx.amount >= 0
                                                ? <ArrowDownLeft className="w-3.5 h-3.5" />
                                                : <ArrowUpRight className="w-3.5 h-3.5" />}
                                            {fmt(Math.abs(tx.amount))}
                                        </p>
                                    </div>
                                    <p className="text-sm text-foreground flex-1 min-w-[160px] truncate" title={tx.description}>
                                        {tx.description}
                                    </p>
                                    {/* Invoice selector */}
                                    <div className="flex items-center gap-2 flex-wrap">
                                        {invoicePool.length === 0 ? (
                                            <span className="text-xs text-muted-foreground italic">Sin coincidencias</span>
                                        ) : (
                                            <>
                                                {suggs.length > 0 && (() => {
                                                    const topScore = suggs[0]?.score ?? 0;
                                                    const tone = topScore >= 80
                                                        ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                                                        : topScore >= 50
                                                            ? "text-amber-400 bg-amber-500/10 border-amber-500/20"
                                                            : "text-muted-foreground bg-muted/30 border-border";
                                                    return (
                                                        <span className={`text-xs font-medium border px-2 py-0.5 rounded-full ${tone}`} title={`Confianza del mejor candidato`}>
                                                            {suggs.length} sugerencia{suggs.length > 1 ? "s" : ""}{topScore ? ` · ${topScore}%` : ""}
                                                        </span>
                                                    );
                                                })()}
                                                <select
                                                    value={sel}
                                                    onChange={(e) => setSelectedInvoice((prev) => ({ ...prev, [tx.id]: e.target.value }))}
                                                    className="bg-muted border border-border rounded-lg px-2 py-1.5 text-xs text-foreground focus:outline-none focus:border-primary/50 max-w-[320px]"
                                                >
                                                    {invoicePool.map((inv) => {
                                                        const suggested = suggs.find(s => s.id === inv.id);
                                                        const scoreLabel = suggested?.score ? ` · ★${suggested.score}` : "";
                                                        return (
                                                            <option key={inv.id} value={inv.id}>
                                                                {inv.invoice_number ?? "S/N"} · {fmt(inv.amount_total)}{inv.client_name ? ` · ${inv.client_name}` : ""}{scoreLabel}
                                                            </option>
                                                        );
                                                    })}
                                                </select>
                                            </>
                                        )}
                                    </div>
                                </div>

                                {/* Right: actions */}
                                <div className="flex items-center gap-2 justify-end">
                                    {invoicePool.length > 0 && (
                                        <Button
                                            size="sm"
                                            disabled={busy || !sel}
                                            onClick={() => handleReconcile(tx.id, sel)}
                                        >
                                            {busy
                                                ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                                : <><Check className="mr-1 h-3.5 w-3.5" />Puntear</>}
                                        </Button>
                                    )}
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="text-muted-foreground hover:text-foreground"
                                        disabled={busy}
                                        onClick={() => handleIgnore(tx.id)}
                                        title="Ignorar (no requiere factura)"
                                    >
                                        <EyeOff className="h-3.5 w-3.5" />
                                    </Button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Reconciled list */}
            {reconciled.length > 0 && (
                <details className="group">
                    <summary className="cursor-pointer text-sm font-semibold text-muted-foreground hover:text-foreground flex items-center gap-2 select-none">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        Conciliadas ({reconciled.length})
                        <span className="text-xs font-normal">(haz clic para expandir)</span>
                    </summary>
                    <div className="mt-3 space-y-2">
                        {reconciled.map((tx) => (
                            <div key={tx.id} className="flex items-center justify-between rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-2.5">
                                <div className="flex items-center gap-4">
                                    <p className="text-xs text-muted-foreground font-mono">{fmtDate(tx.date)}</p>
                                    <p className="text-sm text-foreground truncate max-w-[240px]">{tx.description}</p>
                                    <span className="text-sm font-semibold text-emerald-400 tabular-nums">{fmt(Math.abs(tx.amount))}</span>
                                </div>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="text-muted-foreground hover:text-destructive text-xs gap-1"
                                    disabled={actionId === tx.id}
                                    onClick={() => handleUnreconcile(tx.id)}
                                    title="Deshacer conciliación"
                                >
                                    {actionId === tx.id
                                        ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                        : <Undo2 className="h-3.5 w-3.5" />}
                                    Deshacer
                                </Button>
                            </div>
                        ))}
                    </div>
                </details>
            )}

            {/* Ignored list */}
            {ignored.length > 0 && (
                <details className="group">
                    <summary className="cursor-pointer text-sm font-semibold text-muted-foreground hover:text-foreground flex items-center gap-2 select-none">
                        <EyeOff className="w-4 h-4" />
                        Ignoradas ({ignored.length})
                    </summary>
                    <div className="mt-3 space-y-2">
                        {ignored.map((tx) => (
                            <div key={tx.id} className="flex items-center justify-between rounded-xl border border-border bg-muted/20 px-4 py-2.5 opacity-60 hover:opacity-100 transition-opacity">
                                <div className="flex items-center gap-4">
                                    <p className="text-xs text-muted-foreground font-mono">{fmtDate(tx.date)}</p>
                                    <p className="text-sm text-foreground truncate max-w-[240px]">{tx.description}</p>
                                    <span className="text-sm font-semibold tabular-nums">{fmt(Math.abs(tx.amount))}</span>
                                </div>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="text-muted-foreground hover:text-foreground text-xs gap-1"
                                    disabled={actionId === tx.id}
                                    onClick={() => handleUnreconcile(tx.id)}
                                    title="Restaurar a pendiente"
                                >
                                    <Undo2 className="h-3.5 w-3.5" /> Restaurar
                                </Button>
                            </div>
                        ))}
                    </div>
                </details>
            )}
        </div>
    );
}
