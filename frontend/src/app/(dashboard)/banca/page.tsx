"use client";

import { useEffect, useMemo, useState, useRef, useCallback } from "react";
import { api, type Task } from "@/lib/api";
import {
    Banknote, TrendingUp, TrendingDown, AlertTriangle,
    Link2, RefreshCw, Loader2, ArrowUpRight, ArrowDownLeft,
    Building2, CreditCard, Wifi, WifiOff, FileDown,
} from "lucide-react";
import { ColumnDef } from "@tanstack/react-table";
import { DataTable, DataTableColumnHeader } from "@/components/data-table";
import { PageHeader } from "@/components/shared/PageHeader";
import { KpiCard } from "@/components/shared/KpiCard";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Saldo { account_id: string; iban: string; nombre: string; saldo: number; moneda: string; error?: string; }
interface Transaction { id: string; fecha: string; concepto: string; importe: number; tipo: string; categoria: string; }
import { BankTransaction, Invoice } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { logError } from "@/lib/logger";

const CATEGORY_LABELS: Record<string, string> = {
    proveedor_material: "Material", proveedor_servicio: "Servicios",
    nominas: "Nóminas", impuestos: "Impuestos", alquiler: "Alquiler",
    suministros: "Suministros", financiero: "Financiero",
    cliente_cobro: "Cobros", transferencia_interna: "Interna", otros: "Otros",
};
const CATEGORY_COLOR: Record<string, { text: string; bar: string }> = {
    proveedor_material: { text: "text-orange-400", bar: "bg-orange-400" },
    proveedor_servicio: { text: "text-purple-400", bar: "bg-purple-400" },
    nominas: { text: "text-blue-400", bar: "bg-blue-400" },
    impuestos: { text: "text-red-400", bar: "bg-red-400" },
    alquiler: { text: "text-pink-400", bar: "bg-pink-400" },
    suministros: { text: "text-cyan-400", bar: "bg-cyan-400" },
    financiero: { text: "text-yellow-400", bar: "bg-yellow-400" },
    cliente_cobro: { text: "text-emerald-400", bar: "bg-emerald-400" },
    transferencia_interna: { text: "text-muted-foreground", bar: "bg-muted-foreground" },
    otros: { text: "text-muted-foreground", bar: "bg-muted-foreground" },
};

type Tab = "saldos" | "transacciones" | "resumen";

// ─── Polling Hook ─────────────────────────────────────────────────────────────

function useAgentPolling() {
    const [status, setStatus] = useState<string>("idle");
    const [result, setResult] = useState<unknown>(null);
    const [error, setError] = useState<string | null>(null);
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const stop = useCallback(() => {
        if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }
    }, []);

    const launch = useCallback(async (intent: string) => {
        stop(); setResult(null); setError(null); setStatus("creating");
        try {
            const task = await api.tasks.create("banking", intent);
            setStatus("polling");
            intervalRef.current = setInterval(async () => {
                try {
                    const t: Task = await api.tasks.get(task.id);
                    if (t.status === "done" || t.status === "failed" || t.status === "cancelled") {
                        stop();
                        setStatus(t.status === "done" ? "done" : "failed");
                        setResult(t.agent_results ?? t.plan);
                        if (t.error_message) setError(t.error_message);
                    }
                } catch { /* keep polling */ }
            }, 2000);
        } catch (e) {
            setStatus("failed");
            setError(e instanceof Error ? e.message : "Error al crear la tarea");
        }
    }, [stop]);

    useEffect(() => () => stop(), [stop]);
    return { launch, status, result, error };
}

// ─── Extract result data from agent result array ──────────────────────────────

function extractOutput(result: unknown): Record<string, unknown> {
    if (!result) return {};
    const arr = Array.isArray(result) ? result : [result];
    for (const item of arr) {
        const out = (item as Record<string, unknown>).output ?? item;
        if (typeof out === "object" && out !== null) return out as Record<string, unknown>;
    }
    return {};
}

// ─── SVG Donut Chart ─────────────────────────────────────────────────────────

function DonutChart({ segments }: { segments: { label: string; value: number; color: string }[] }) {
    const total = segments.reduce((s, x) => s + Math.abs(x.value), 0);
    if (total === 0) return null;

    const r = 52, cx = 60, cy = 60, stroke = 16;
    const circumference = 2 * Math.PI * r;
    let offset = 0;

    return (
        <svg width={120} height={120} viewBox="0 0 120 120" className="rotate-[-90deg]">
            {segments.map((seg, i) => {
                const pct = Math.abs(seg.value) / total;
                const dash = pct * circumference;
                const gap = circumference - dash;
                const el = (
                    <circle key={i} cx={cx} cy={cy} r={r}
                        fill="none" stroke={seg.color} strokeWidth={stroke}
                        strokeDasharray={`${dash} ${gap}`}
                        strokeDashoffset={-offset}
                        className="transition-all duration-700"
                    />
                );
                offset += dash;
                return el;
            })}
        </svg>
    );
}

// ─── Bar Sparkline ────────────────────────────────────────────────────────────

function BarSparkline({ values, color = "#6366f1" }: { values: number[]; color?: string }) {
    const max = Math.max(...values.map(Math.abs), 1);
    return (
        <div className="flex items-end gap-0.5 h-12">
            {values.map((v, i) => (
                <div key={i}
                    style={{ height: `${(Math.abs(v) / max) * 100}%`, backgroundColor: color, opacity: 0.7 + (i / values.length) * 0.3 }}
                    className="flex-1 rounded-sm transition-all duration-500"
                />
            ))}
        </div>
    );
}

// ─── Loader ──────────────────────────────────────────────────────────────────

function AgentLoader({ label }: { label: string }) {
    return (
        <div className="flex flex-col items-center gap-4 py-12">
            <div className="w-10 h-10 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />
            <p className="text-sm text-muted-foreground">{label}</p>
        </div>
    );
}

// ─── Transaction Columns ─────────────────────────────────────────────────────

function getTransactionColumns(onReconcile: (tx: BankTransaction) => void): ColumnDef<BankTransaction, any>[] {
    return [
        {
            accessorKey: "date",
            header: ({ column }) => <DataTableColumnHeader column={column} title="Fecha" />,
            cell: ({ row }) => (
                <span className="text-xs text-muted-foreground font-mono">{row.original.date}</span>
            ),
        },
        {
            accessorKey: "description",
            header: ({ column }) => <DataTableColumnHeader column={column} title="Concepto" />,
            cell: ({ row }) => (
                <span className="text-sm text-foreground truncate block max-w-[300px]" title={row.original.description}>
                    {row.original.description}
                </span>
            ),
        },
        {
            accessorKey: "status",
            header: ({ column }) => <DataTableColumnHeader column={column} title="Estado" />,
            cell: ({ row }) => (
                <StatusBadge
                    status={row.original.status}
                    label={row.original.status === "reconciled" ? "Conciliada" : "Pendiente"}
                />
            ),
            filterFn: (row, id, value) => value.includes(row.getValue(id)),
        },
        {
            accessorKey: "amount",
            header: ({ column }) => <DataTableColumnHeader column={column} title="Importe" />,
            cell: ({ row }) => {
                const amount = row.original.amount;
                return (
                    <div className={`text-sm font-semibold flex items-center gap-1 tabular-nums ${amount >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                        {amount >= 0 ? <ArrowDownLeft className="w-3 h-3" /> : <ArrowUpRight className="w-3 h-3" />}
                        {amount >= 0 ? "+" : ""}{amount.toLocaleString("es-ES", { minimumFractionDigits: 2 })}€
                    </div>
                );
            },
        },
        {
            id: "actions",
            header: () => <span className="sr-only">Acciones</span>,
            cell: ({ row }) => {
                const tx = row.original;
                if (tx.status === "reconciled") return null;
                return (
                    <Button variant="ghost" size="sm" onClick={() => onReconcile(tx)} className="text-xs text-primary hover:text-primary">
                        Conciliar
                    </Button>
                );
            },
        },
    ];
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function BancaPage() {
    const [tab, setTab] = useState<Tab>("saldos");
    const tabs: { id: Tab; label: string; icon: React.ElementType }[] = [
        { id: "saldos", label: "Saldos", icon: Banknote },
        { id: "transacciones", label: "Transacciones", icon: RefreshCw },
        { id: "resumen", label: "Resumen del mes", icon: TrendingUp },
    ];

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Banca PSD2"
                description="Visión financiera en tiempo real de tus cuentas bancarias"
                icon={Banknote}
                actions={
                    <Button variant="outline" asChild>
                        <a href="/integraciones">
                            <Link2 className="mr-2 h-4 w-4" /> Conectar banco
                        </a>
                    </Button>
                }
            />

            {/* Tabs */}
            <div className="flex gap-1 p-1 rounded-xl bg-card border border-border w-fit">
                {tabs.map(({ id, label, icon: Icon }) => (
                    <button key={id} onClick={() => setTab(id)}
                        className={`flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-medium transition-all duration-200
                            ${tab === id ? "bg-primary text-primary-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}>
                        <Icon className="w-4 h-4" /> {label}
                    </button>
                ))}
            </div>

            {tab === "saldos" && <SaldosTab />}
            {tab === "transacciones" && <TransaccionesTab />}
            {tab === "resumen" && <ResumenTab />}
        </div>
    );
}

// ─── Saldos Tab ───────────────────────────────────────────────────────────────

function SaldosTab() {
    const { launch, status, result, error } = useAgentPolling();
    const output = extractOutput(result);
    const saldos = (output.saldos ?? output.balances ?? []) as Saldo[];
    const alertas = (output.alertas ?? []) as string[];
    const isDemo = alertas.some(a => a.toLowerCase().includes("demo"));
    const totalSaldo = saldos.reduce((s, c) => s + (c.saldo ?? 0), 0);

    useEffect(() => { launch("saldo balance cuentas"); }, []);  // eslint-disable-line react-hooks/exhaustive-deps

    if (status === "creating" || status === "polling") return <AgentLoader label="Consultando cuentas…" />;

    return (
        <div className="space-y-6">
            {/* Demo banner */}
            {isDemo && (
                <div className="flex items-center gap-3 px-4 py-3 rounded-xl border border-warning/20 bg-warning/5 text-warning text-sm">
                    <WifiOff className="w-4 h-4 flex-shrink-0" />
                    <span>Banco no conectado — datos de demostración. <a href="/integraciones" className="underline hover:opacity-80">Conectar banco real</a></span>
                </div>
            )}

            {error && (
                <div className="px-4 py-3 rounded-xl border border-destructive/20 bg-destructive/5 text-destructive text-sm">{error}</div>
            )}

            {/* Saldo total hero */}
            <Card className="border-primary/20 bg-gradient-to-br from-primary/10 to-transparent">
                <CardContent className="p-7">
                    <p className="text-xs text-muted-foreground uppercase tracking-widest mb-2">Saldo total consolidado</p>
                    <p className="text-5xl font-bold text-foreground tabular-nums">
                        {totalSaldo.toLocaleString("es-ES", { minimumFractionDigits: 2 })}
                        <span className="text-2xl text-muted-foreground ml-2">€</span>
                    </p>
                    {saldos.length > 0 && (
                        <p className="text-xs text-muted-foreground mt-3">{saldos.length} cuenta{saldos.length !== 1 ? "s" : ""} vinculada{saldos.length !== 1 ? "s" : ""}</p>
                    )}
                </CardContent>
            </Card>

            {/* Account cards */}
            {saldos.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {saldos.map((acc) => (
                        <Card key={acc.account_id} className="hover:border-primary/30 transition">
                            <CardContent className="p-6 flex items-start gap-4">
                                <div className="p-3 rounded-xl bg-primary/10 border border-primary/20 flex-shrink-0">
                                    <Building2 className="w-5 h-5 text-primary" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="text-foreground font-medium text-sm truncate">{acc.nombre}</p>
                                    <p className="text-xs text-muted-foreground font-mono mt-0.5 truncate">{acc.iban}</p>
                                    <p className={`text-2xl font-bold mt-3 tabular-nums ${acc.saldo < 1000 ? "text-destructive" : "text-emerald-400"}`}>
                                        {(acc.saldo ?? 0).toLocaleString("es-ES", { minimumFractionDigits: 2 })}€
                                    </p>
                                </div>
                                {acc.saldo < 1000 && (
                                    <AlertTriangle className="w-4 h-4 text-warning flex-shrink-0 mt-1" />
                                )}
                            </CardContent>
                        </Card>
                    ))}
                </div>
            ) : (
                <EmptyState
                    icon={CreditCard}
                    title="Sin cuentas disponibles"
                    description="Conecta tu banco para ver tus cuentas y saldos en tiempo real."
                    action={
                        <Button variant="outline" asChild>
                            <a href="/integraciones"><Link2 className="mr-2 h-4 w-4" /> Conectar banco</a>
                        </Button>
                    }
                />
            )}

            {/* Alertas */}
            {alertas.filter(a => !a.toLowerCase().includes("demo")).map((a, i) => (
                <div key={i} className="flex items-center gap-3 px-4 py-3 rounded-xl border border-warning/20 bg-warning/5 text-warning text-sm">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0" /> {a}
                </div>
            ))}

            {/* Refresh */}
            <Button variant="ghost" size="sm" onClick={() => launch("saldo balance cuentas")} className="text-muted-foreground">
                <RefreshCw className="mr-2 h-3.5 w-3.5" /> Actualizar
            </Button>
        </div>
    );
}

// ─── Transacciones Tab ────────────────────────────────────────────────────────

function TransaccionesTab() {
    const toast = useToastStore();
    const [txList, setTxList] = useState<BankTransaction[]>([]);
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [isSyncing, setIsSyncing] = useState(false);
    const [isLoading, setIsLoading] = useState(true);

    const [dateFrom, setDateFrom] = useState("");
    const [dateTo, setDateTo] = useState("");

    // Modal state for reconcile
    const [reconcileTx, setReconcileTx] = useState<BankTransaction | null>(null);
    const [selectedInvoice, setSelectedInvoice] = useState("");
    const [reconciling, setReconciling] = useState(false);

    useEffect(() => { loadData(); }, []);

    const loadData = async () => {
        setIsLoading(true);
        try {
            const [txData, invData] = await Promise.all([
                api.banking.transactions.list(),
                api.erp.invoices.list()
            ]);
            setTxList(txData);
            setInvoices(invData.filter(i => i.status !== "paid"));
        } catch (error) {
            logError("banca/page", error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSync = async () => {
        setIsSyncing(true);
        try {
            await api.banking.transactions.sync();
            await loadData();
        } catch (error) {
            logError("banca/page", error);
        } finally {
            setIsSyncing(false);
        }
    };

    const handleReconcile = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedInvoice || !reconcileTx) return;
        setReconciling(true);
        try {
            await api.banking.transactions.reconcile(reconcileTx.id, selectedInvoice);
            setReconcileTx(null);
            setSelectedInvoice("");
            await loadData();
        } catch (error) {
            logError("banca/page", error);
            toast.error("Error al conciliar la transacción.");
        } finally {
            setReconciling(false);
        }
    };

    const filteredTx = useMemo(() => {
        return txList.filter(tx => {
            if (!tx.date) return true;
            const d = tx.date.slice(0, 10);
            if (dateFrom && d < dateFrom) return false;
            if (dateTo && d > dateTo) return false;
            return true;
        });
    }, [txList, dateFrom, dateTo]);

    const ingresos = filteredTx.filter(t => t.amount > 0).reduce((s, t) => s + t.amount, 0);
    const gastos = filteredTx.filter(t => t.amount < 0).reduce((s, t) => s + Math.abs(t.amount), 0);

    const columns = getTransactionColumns((tx) => setReconcileTx(tx));

    const statusFilterOptions = [
        { label: "Pendiente", value: "pending" },
        { label: "Conciliada", value: "reconciled" },
    ];

    const exportCsv = () => {
        const header = "Fecha;Concepto;Importe;Estado\n";
        const rows = filteredTx.map(tx =>
            `${tx.date};"${(tx.description || "").replace(/"/g, '""')}";${tx.amount.toFixed(2).replace(".", ",")};${tx.status === "reconciled" ? "Conciliada" : "Pendiente"}`
        ).join("\n");
        const blob = new Blob([header + rows], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `movimientos_${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    return (
        <div className="space-y-6">
            {/* KPI row */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <KpiCard title="Ingresos" value={`+${ingresos.toLocaleString("es-ES", { minimumFractionDigits: 2 })}€`} icon={TrendingUp} />
                <KpiCard title="Gastos" value={`-${gastos.toLocaleString("es-ES", { minimumFractionDigits: 2 })}€`} icon={TrendingDown} />
                <KpiCard title="Neto" value={`${ingresos - gastos >= 0 ? "+" : ""}${(ingresos - gastos).toLocaleString("es-ES", { minimumFractionDigits: 2 })}€`} icon={Banknote} />
            </div>

            {/* Filters + actions */}
            <div className="flex flex-wrap items-end justify-between gap-4">
                <div className="flex flex-wrap items-end gap-3">
                    <div>
                        <label className="block text-xs font-medium text-muted-foreground mb-1">Desde</label>
                        <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)}
                            className="bg-muted border border-border rounded-xl px-3 py-2 text-foreground text-sm outline-none focus:border-primary/20" />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-muted-foreground mb-1">Hasta</label>
                        <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)}
                            className="bg-muted border border-border rounded-xl px-3 py-2 text-foreground text-sm outline-none focus:border-primary/20" />
                    </div>
                    {(dateFrom || dateTo) && (
                        <Button variant="ghost" size="sm" onClick={() => { setDateFrom(""); setDateTo(""); }}>
                            Limpiar fechas
                        </Button>
                    )}
                </div>
                <div className="flex items-center gap-2">
                    <Button size="sm" variant="outline" onClick={exportCsv} disabled={filteredTx.length === 0}>
                        <FileDown className="mr-2 h-3 w-3" /> Exportar CSV
                    </Button>
                    <Button size="sm" onClick={handleSync} disabled={isSyncing}>
                        {isSyncing ? <Loader2 className="mr-2 h-3 w-3 animate-spin" /> : <RefreshCw className="mr-2 h-3 w-3" />}
                        {isSyncing ? "Sincronizando…" : "Descargar movimientos"}
                    </Button>
                </div>
            </div>

            {/* Transaction DataTable */}
            <DataTable
                columns={columns}
                data={filteredTx}
                isLoading={isLoading}
                searchKey="description"
                searchPlaceholder="Buscar por concepto…"
                emptyMessage="Pulsa en 'Descargar movimientos' para importar desde tu banco."
                facetedFilters={[
                    { column: "status", title: "Estado", options: statusFilterOptions },
                ]}
            />

            {/* Modal Conciliación */}
            {reconcileTx && (
                <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" onClick={() => setReconcileTx(null)}>
                    <Card className="w-full max-w-md" onClick={e => e.stopPropagation()}>
                        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                            <h2 className="font-semibold text-foreground text-sm">Conciliar Transacción</h2>
                        </div>
                        <form onSubmit={handleReconcile} className="p-6 space-y-4">
                            <div className="bg-muted/50 p-3 rounded-lg border border-border">
                                <p className="text-xs text-muted-foreground font-mono mb-1">{reconcileTx.date}</p>
                                <p className="text-sm text-foreground font-medium mb-1">{reconcileTx.description}</p>
                                <p className={`text-lg font-bold ${reconcileTx.amount >= 0 ? "text-emerald-400" : "text-destructive"}`}>
                                    {reconcileTx.amount} €
                                </p>
                            </div>
                            <div>
                                <label className="text-sm text-foreground block mb-1.5 font-medium">Asociar facturas pendientes</label>
                                <select required value={selectedInvoice} onChange={e => setSelectedInvoice(e.target.value)}
                                    className="w-full px-3 py-2.5 rounded-lg bg-background border border-border text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring">
                                    <option value="">-- Selecciona factura --</option>
                                    {invoices.map(inv => (
                                        <option key={inv.id} value={inv.id}>
                                            {inv.invoice_number || "S/N"} - {inv.amount_total}€ (Cl: {inv.client?.name})
                                        </option>
                                    ))}
                                </select>
                                {invoices.length === 0 && <p className="text-xs text-destructive mt-2">No tienes facturas pendientes con pagos.</p>}
                            </div>

                            <div className="flex gap-3 pt-2">
                                <Button type="button" variant="outline" className="flex-1" onClick={() => setReconcileTx(null)}>
                                    Cancelar
                                </Button>
                                <Button type="submit" className="flex-1" disabled={reconciling || invoices.length === 0 || !selectedInvoice}>
                                    {reconciling ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                                    Puntear (Conciliar)
                                </Button>
                            </div>
                        </form>
                    </Card>
                </div>
            )}
        </div>
    );
}

// ─── Resumen Tab ──────────────────────────────────────────────────────────────

function ResumenTab() {
    const { launch, status, result, error } = useAgentPolling();
    const output = extractOutput(result);
    const resumenTexto = (output.resumen_financiero ?? output.resumen ?? null) as string | null;
    const saldos = (output.saldos ?? []) as Saldo[];
    const alertas = (output.alertas ?? []) as string[];
    const isDemo = alertas.some(a => a.toLowerCase().includes("demo"));

    // Metric State
    const [metrics, setMetrics] = useState({ ingresos: 18500, gastos: 12730, neto: 5770, margen: 31, isDemo: true });

    // Extraer desglose por categoría (dinámico)
    const porCategoriaRaw = output.por_categoria as Record<string, { total: number; operaciones: number }> | undefined;

    const catColors: Record<string, string> = {
        nominas: "#60a5fa", proveedor_servicio: "#c084fc", suministros: "#22d3ee",
        financiero: "#facc15", alquiler: "#f472b6", proveedor_material: "#fb923c",
        impuestos: "#f87171", otros: "#71717a"
    };
    const catLabels: Record<string, string> = {
        nominas: "Nóminas", proveedor_servicio: "Soft/Servicios", suministros: "Suministros",
        financiero: "Financiero", alquiler: "Alquileres", proveedor_material: "Materiales",
        impuestos: "Impuestos"
    };

    let categorias = [
        { label: "Nóminas", value: 7000, color: "#60a5fa" },
        { label: "Proveedores", value: 2800, color: "#c084fc" },
        { label: "Suministros", value: 1500, color: "#22d3ee" },
        { label: "Financiero", value: 1100, color: "#facc15" },
        { label: "Otros", value: 330, color: "#71717a" },
    ];

    if (porCategoriaRaw) {
        const gastosCat = Object.entries(porCategoriaRaw)
            .filter(([_, data]) => data.total < 0)
            .map(([cat, data]) => ({
                label: catLabels[cat] || "Otros",
                value: Math.abs(data.total),
                color: catColors[cat] || catColors.otros
            }))
            .sort((a, b) => b.value - a.value);
        if (gastosCat.length > 0) categorias = gastosCat;
    }

    const totalGastos = categorias.reduce((s, c) => s + c.value, 0);

    // Monthly sparkline
    const mensual = metrics.isDemo ? [] : [metrics.neto];

    useEffect(() => {
        api.banking.summary().then((d) => {
            setMetrics({
                ingresos: d.ingresos,
                gastos: d.gastos,
                neto: d.neto,
                margen: d.margen,
                isDemo: d.is_demo
            });
        }).catch(err => useToastStore.getState().error(err?.message || "Error al cargar datos bancarios"));

        launch("resumen financiero mes");
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    return (
        <div className="space-y-6">
            {/* Demo banner */}
            {(isDemo || metrics.isDemo) && (
                <div className="flex items-center gap-3 px-4 py-3 rounded-xl border border-warning/20 bg-warning/5 text-warning text-sm">
                    <WifiOff className="w-4 h-4 flex-shrink-0" />
                    <span>Esta cuenta es nueva y no tiene datos históricos. Estás viendo información precalculada de demostración para las tarjetas de resumen. <a href="/integraciones" className="underline hover:opacity-80">Conecta tu banco real</a> y registra facturas para ver métricas en vivo.</span>
                </div>
            )}
            {error && <div className="px-4 py-3 rounded-xl border border-destructive/20 bg-destructive/5 text-destructive text-sm">{error}</div>}

            {/* KPI cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <KpiCard title="Ingresos" value={`+${metrics.ingresos.toLocaleString("es-ES")}€`} icon={TrendingUp} />
                <KpiCard title="Gastos" value={`-${metrics.gastos.toLocaleString("es-ES")}€`} icon={TrendingDown} />
                <KpiCard title="Resultado neto" value={`${metrics.neto >= 0 ? "+" : ""}${metrics.neto.toLocaleString("es-ES")}€`} icon={Banknote} />
                <KpiCard title="Margen" value={`${metrics.margen}%`} icon={Wifi} />
            </div>

            {/* Charts row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Donut — Desglose gastos */}
                <Card>
                    <CardContent className="p-6">
                        <p className="text-sm font-medium text-foreground mb-5">Desglose de gastos</p>
                        <div className="flex items-center gap-6">
                            <div className="relative flex-shrink-0">
                                <DonutChart segments={categorias} />
                                <div className="absolute inset-0 flex items-center justify-center flex-col">
                                    <span className="text-xs text-muted-foreground">Total</span>
                                    <span className="text-sm font-bold text-foreground">{totalGastos.toLocaleString("es-ES")}€</span>
                                </div>
                            </div>
                            <div className="flex-1 space-y-2.5">
                                {categorias.map(c => (
                                    <div key={c.label}>
                                        <div className="flex justify-between text-xs mb-1">
                                            <span className="text-muted-foreground">{c.label}</span>
                                            <span className="text-foreground tabular-nums">{c.value.toLocaleString("es-ES")}€</span>
                                        </div>
                                        <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                                            <div className="h-full rounded-full transition-all duration-700"
                                                style={{ width: `${(c.value / totalGastos) * 100}%`, backgroundColor: c.color }} />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Sparkline — Tendencia neta */}
                <Card>
                    <CardContent className="p-6">
                        <div className="flex items-start justify-between mb-5">
                            <p className="text-sm font-medium text-foreground">Resultado neto mensual</p>
                            <span className="text-xs text-muted-foreground">Últimos 6 meses</span>
                        </div>
                        {mensual.length === 0 ? (
                            <div className="h-[60px] flex items-center justify-center text-sm text-muted-foreground">Conecta tu banco para ver la tendencia</div>
                        ) : (
                        <>
                        <BarSparkline values={mensual} color={metrics.neto >= 0 ? "#6366f1" : "#ef4444"} />
                        <div className="flex justify-between mt-2">
                            {["Sep", "Oct", "Nov", "Dic", "Ene", "Feb"].map((m, i) => (
                                <span key={i} className="text-xs text-muted-foreground/60">{m}</span>
                            ))}
                        </div>
                        </>
                        )}
                        {/* Margin gauge */}
                        <div className="mt-6 pt-5 border-t border-border">
                            <div className="flex justify-between text-xs mb-2">
                                <span className="text-muted-foreground">Margen sobre ingresos</span>
                                <span className="font-bold text-primary">{metrics.margen}%</span>
                            </div>
                            <div className="h-2 rounded-full bg-muted overflow-hidden">
                                <div className="h-full rounded-full bg-gradient-to-r from-primary to-primary/60 transition-all duration-1000"
                                    style={{ width: `${Math.min(100, Math.max(0, metrics.margen))}%` }} />
                            </div>
                            <p className="text-xs text-muted-foreground/60 mt-1.5">
                                {metrics.margen >= 30 ? "Margen saludable" : metrics.margen >= 15 ? "Margen ajustado" : "Margen bajo"}
                            </p>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* AI summary text */}
            <Card>
                <CardContent className="p-6">
                    <div className="flex items-center justify-between mb-4">
                        <p className="text-sm font-medium text-foreground">Análisis del agente IA</p>
                        <Button variant="ghost" size="sm"
                            onClick={() => launch("resumen financiero mes")}
                            disabled={status === "polling" || status === "creating"}
                            className="text-muted-foreground"
                        >
                            {status === "polling" || status === "creating" ? <Loader2 className="mr-1.5 h-3 w-3 animate-spin" /> : <RefreshCw className="mr-1.5 h-3 w-3" />}
                            {status === "polling" ? "Generando…" : "Regenerar"}
                        </Button>
                    </div>
                    {status === "creating" || status === "polling" ? (
                        <div className="flex items-center gap-3 text-muted-foreground text-sm py-4">
                            <Loader2 className="w-4 h-4 animate-spin" /> El agente está analizando tus finanzas…
                        </div>
                    ) : (
                        <p className="text-sm text-foreground leading-relaxed whitespace-pre-line">
                            {resumenTexto ?? "Haz clic en Regenerar para que la IA analice tus movimientos del mes y genere recomendaciones personalizadas."}
                        </p>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
