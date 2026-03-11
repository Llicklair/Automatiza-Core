"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { api, type Task } from "@/lib/api";
import {
    Banknote, TrendingUp, TrendingDown, AlertTriangle,
    Link2, RefreshCw, Loader2, ArrowUpRight, ArrowDownLeft,
    Building2, CreditCard, Wifi, WifiOff,
} from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Saldo { account_id: string; iban: string; nombre: string; saldo: number; moneda: string; error?: string; }
interface Transaction { id: string; fecha: string; concepto: string; importe: number; tipo: string; categoria: string; }
import { BankTransaction, Invoice } from "@/lib/api";
import { useToastStore } from "@/stores/toast";

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
    transferencia_interna: { text: "text-zinc-400", bar: "bg-zinc-400" },
    otros: { text: "text-zinc-500", bar: "bg-zinc-500" },
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
            <div className="w-10 h-10 rounded-full border-2 border-indigo-500/30 border-t-indigo-500 animate-spin" />
            <p className="text-sm text-zinc-400">{label}</p>
        </div>
    );
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
        <div className="p-8 max-w-6xl mx-auto space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white">Banca PSD2</h1>
                    <p className="text-sm text-zinc-400 mt-1">Visión financiera en tiempo real de tus cuentas bancarias</p>
                </div>
                <a href="/integraciones"
                    className="flex items-center gap-2 px-4 py-2 rounded-lg border border-[#27272a] text-zinc-400 hover:text-white hover:border-zinc-500 text-sm transition">
                    <Link2 className="w-4 h-4" /> Conectar banco
                </a>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 p-1 rounded-xl bg-[#18181b] border border-[#27272a] w-fit">
                {tabs.map(({ id, label, icon: Icon }) => (
                    <button key={id} onClick={() => setTab(id)}
                        className={`flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-medium transition-all duration-200
                            ${tab === id ? "bg-indigo-600 text-white shadow-[0_0_12px_rgba(99,102,241,0.4)]" : "text-zinc-400 hover:text-white"}`}>
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
                <div className="flex items-center gap-3 px-4 py-3 rounded-xl border border-amber-500/20 bg-amber-500/5 text-amber-400 text-sm">
                    <WifiOff className="w-4 h-4 flex-shrink-0" />
                    <span>Banco no conectado — datos de demostración. <a href="/integraciones" className="underline hover:text-amber-300">Conectar banco real</a></span>
                </div>
            )}

            {error && (
                <div className="px-4 py-3 rounded-xl border border-red-500/20 bg-red-500/5 text-red-400 text-sm">{error}</div>
            )}

            {/* Saldo total hero */}
            <div className="rounded-2xl border border-indigo-500/20 bg-gradient-to-br from-indigo-600/10 to-indigo-900/5 p-7">
                <p className="text-xs text-zinc-500 uppercase tracking-widest mb-2">Saldo total consolidado</p>
                <p className="text-5xl font-bold text-white tabular-nums">
                    {totalSaldo.toLocaleString("es-ES", { minimumFractionDigits: 2 })}
                    <span className="text-2xl text-zinc-400 ml-2">€</span>
                </p>
                {saldos.length > 0 && (
                    <p className="text-xs text-zinc-500 mt-3">{saldos.length} cuenta{saldos.length !== 1 ? "s" : ""} vinculada{saldos.length !== 1 ? "s" : ""}</p>
                )}
            </div>

            {/* Account cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {saldos.length > 0 ? saldos.map((acc) => (
                    <div key={acc.account_id} className="rounded-xl border border-[#27272a] bg-[#111113] p-6 flex items-start gap-4 hover:border-zinc-600 transition">
                        <div className="p-3 rounded-xl bg-indigo-600/10 border border-indigo-500/20 flex-shrink-0">
                            <Building2 className="w-5 h-5 text-indigo-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-white font-medium text-sm truncate">{acc.nombre}</p>
                            <p className="text-xs text-zinc-500 font-mono mt-0.5 truncate">{acc.iban}</p>
                            <p className={`text-2xl font-bold mt-3 tabular-nums ${acc.saldo < 1000 ? "text-red-400" : "text-emerald-400"}`}>
                                {(acc.saldo ?? 0).toLocaleString("es-ES", { minimumFractionDigits: 2 })}€
                            </p>
                        </div>
                        {acc.saldo < 1000 && (
                            <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-1" />
                        )}
                    </div>
                )) : (
                    <div className="col-span-2 py-12 text-center text-zinc-500 text-sm">
                        <CreditCard className="w-10 h-10 mx-auto mb-3 opacity-30" />
                        Sin cuentas disponibles
                    </div>
                )}
            </div>

            {/* Alertas */}
            {alertas.filter(a => !a.toLowerCase().includes("demo")).map((a, i) => (
                <div key={i} className="flex items-center gap-3 px-4 py-3 rounded-xl border border-amber-500/20 bg-amber-500/5 text-amber-300 text-sm">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0" /> {a}
                </div>
            ))}

            {/* Refresh */}
            <button onClick={() => launch("saldo balance cuentas")}
                className="flex items-center gap-2 text-xs text-zinc-500 hover:text-zinc-300 transition">
                <RefreshCw className="w-3.5 h-3.5" /> Actualizar
            </button>
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
            console.error(error);
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
            console.error("Error syncing transactions", error);
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
            console.error(error);
            toast.error("Error al conciliar la transacción.");
        } finally {
            setReconciling(false);
        }
    };

    const ingresos = txList.filter(t => t.amount > 0).reduce((s, t) => s + t.amount, 0);
    const gastos = txList.filter(t => t.amount < 0).reduce((s, t) => s + Math.abs(t.amount), 0);
    const isLive = txList.length > 0;

    return (
        <div className="space-y-6">
            {/* KPI row */}
            <div className="grid grid-cols-3 gap-4">
                {[
                    { label: "Ingresos", value: ingresos, icon: TrendingUp, color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20" },
                    { label: "Gastos", value: -gastos, icon: TrendingDown, color: "text-red-400", bg: "bg-red-500/10", border: "border-red-500/20" },
                    { label: "Neto", value: ingresos - gastos, icon: Banknote, color: ingresos - gastos >= 0 ? "text-indigo-400" : "text-red-400", bg: "bg-indigo-500/10", border: "border-indigo-500/20" },
                ].map(({ label, value, icon: Icon, color, bg, border }) => (
                    <div key={label} className={`rounded-xl border ${border} ${bg} p-5`}>
                        <div className={`inline-flex p-2 rounded-lg bg-black/20 mb-3`}><Icon className={`w-4 h-4 ${color}`} /></div>
                        <p className={`text-xl font-bold tabular-nums ${color}`}>
                            {value >= 0 ? "+" : ""}{value.toLocaleString("es-ES", { minimumFractionDigits: 2 })}€
                        </p>
                        <p className="text-xs text-zinc-500 mt-1">{label}</p>
                    </div>
                ))}
            </div>

            {/* Table header */}
            <div className="flex items-center justify-between">
                <p className="text-xs text-zinc-500">{isLive ? `${txList.length} transacciones registradas` : "Aparecerán aquí las transacciones sincronizadas con el banco."}</p>
                <button onClick={handleSync}
                    disabled={isSyncing}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium transition">
                    {isSyncing ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
                    {isSyncing ? "Sincronizando con banco…" : "Descargar movimientos"}
                </button>
            </div>

            {/* Transaction list */}
            <div className="rounded-xl border border-[#27272a] bg-[#111113] overflow-hidden">
                <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#27272a] text-xs font-medium text-zinc-500 uppercase tracking-wide">
                    <div className="col-span-2">Fecha</div><div className="col-span-4">Concepto</div>
                    <div className="col-span-3">Estado</div><div className="col-span-2 text-right">Importe</div>
                    <div className="col-span-1 text-center">Acción</div>
                </div>
                {isLoading ? (
                    <div className="p-8 text-center text-zinc-500"><Loader2 className="w-6 h-6 animate-spin mx-auto" /></div>
                ) : !isLive ? (
                    <div className="p-12 text-center text-zinc-500">Pulsa en &quot;Descargar movimientos&quot; para importar desde tu Banco.</div>
                ) : txList.map((tx) => (
                    <div key={tx.id}
                        className="grid grid-cols-12 gap-4 px-6 py-3.5 border-b border-[#27272a] last:border-0 items-center hover:bg-white/[0.02] transition">
                        <div className="col-span-2 text-xs text-zinc-400 font-mono">{tx.date}</div>
                        <div className="col-span-4 text-sm text-white truncate" title={tx.description}>{tx.description}</div>
                        <div className="col-span-3">
                            <span className={`text-xs px-2 py-0.5 rounded-full border ${tx.status === "reconciled" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-zinc-800/80 text-zinc-400 border-zinc-700"} `}>
                                {tx.status === "reconciled" ? "Conciliada" : "Pendiente de Puntr"}
                            </span>
                        </div>
                        <div className={`col-span-2 text-sm font-semibold text-right flex items-center justify-end gap-1 tabular-nums
                            ${tx.amount >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                            {tx.amount >= 0 ? <ArrowDownLeft className="w-3 h-3" /> : <ArrowUpRight className="w-3 h-3" />}
                            {tx.amount >= 0 ? "+" : ""}{tx.amount.toLocaleString("es-ES", { minimumFractionDigits: 2 })}€
                        </div>
                        <div className="col-span-1 text-right">
                            {tx.status !== "reconciled" && (
                                <button onClick={() => setReconcileTx(tx)} className="text-xs text-indigo-400 hover:text-indigo-300 underline">
                                    Conciliar
                                </button>
                            )}
                        </div>
                    </div>
                ))}
            </div>

            {/* Modal Conciliación */}
            {reconcileTx && (
                <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" onClick={() => setReconcileTx(null)}>
                    <div className="w-full max-w-md rounded-2xl border border-[#27272a] bg-[#111113] overflow-hidden" onClick={e => e.stopPropagation()}>
                        <div className="flex items-center justify-between px-6 py-4 border-b border-[#27272a]">
                            <h2 className="font-semibold text-white text-sm">Conciliar Transacción</h2>
                        </div>
                        <form onSubmit={handleReconcile} className="p-6 space-y-4">
                            <div className="bg-[#18181b] p-3 rounded-lg border border-zinc-800">
                                <p className="text-xs text-zinc-400 font-mono mb-1">{reconcileTx.date}</p>
                                <p className="text-sm text-white font-medium mb-1">{reconcileTx.description}</p>
                                <p className={`text-lg font-bold ${reconcileTx.amount >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                                    {reconcileTx.amount} €
                                </p>
                            </div>
                            <div>
                                <label className="text-sm text-zinc-300 block mb-1.5 font-medium">Asociar facturas pendientes</label>
                                <select required value={selectedInvoice} onChange={e => setSelectedInvoice(e.target.value)}
                                    className="w-full px-3 py-2.5 rounded-lg bg-[#18181b] border border-[#3f3f46] text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
                                    <option value="">-- Selecciona factura --</option>
                                    {invoices.map(inv => (
                                        <option key={inv.id} value={inv.id}>
                                            {inv.invoice_number || "S/N"} - {inv.amount_total}€ (Cl: {inv.client?.name})
                                        </option>
                                    ))}
                                </select>
                                {invoices.length === 0 && <p className="text-xs text-red-400 mt-2">No tienes facturas pendientes con pagos.</p>}
                            </div>

                            <div className="flex gap-3 pt-2">
                                <button type="button" onClick={() => setReconcileTx(null)}
                                    className="flex-1 py-2.5 rounded-xl border border-[#3f3f46] text-zinc-400 text-sm hover:text-white transition">Cancelar</button>
                                <button type="submit" disabled={reconciling || invoices.length === 0 || !selectedInvoice}
                                    className="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium transition flex items-center justify-center gap-2">
                                    {reconciling ? <Loader2 className="w-4 h-4 animate-spin" /> : "Puntear (Conciliar)"}
                                </button>
                            </div>
                        </form>
                    </div>
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
        // Ignorar categorías con valor > 0 (asumimos ingresos)
        const gastosCat = Object.entries(porCategoriaRaw)
            .filter(([_, data]) => data.total < 0)
            .map(([cat, data]) => ({
                label: catLabels[cat] || "Otros",
                value: Math.abs(data.total),
                color: catColors[cat] || catColors.otros
            }))
            .sort((a, b) => b.value - a.value); // Ordenar por importe
        if (gastosCat.length > 0) categorias = gastosCat;
    }

    const totalGastos = categorias.reduce((s, c) => s + c.value, 0);

    // Monthly sparkline — only current month neto when no history available
    const mensual = metrics.isDemo ? [] : [metrics.neto];

    useEffect(() => {
        // Cargar los KPIs estáticos desde backend
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
                <div className="flex items-center gap-3 px-4 py-3 rounded-xl border border-amber-500/20 bg-amber-500/5 text-amber-400 text-sm">
                    <WifiOff className="w-4 h-4 flex-shrink-0" />
                    <span>Esta cuenta es nueva y no tiene datos históricos. Estás viendo información precalculada de demostración para las tarjetas de resumen. <a href="/integraciones" className="underline hover:text-amber-300">Conecta tu banco real</a> y registra facturas para ver métricas en vivo.</span>
                </div>
            )}
            {error && <div className="px-4 py-3 rounded-xl border border-red-500/20 bg-red-500/5 text-red-400 text-sm">{error}</div>}

            {/* KPI cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                    { label: "Ingresos", value: `+${metrics.ingresos.toLocaleString("es-ES")}€`, icon: TrendingUp, color: "text-emerald-400", bg: "from-emerald-600/10 to-transparent", border: "border-emerald-500/20" },
                    { label: "Gastos", value: `-${metrics.gastos.toLocaleString("es-ES")}€`, icon: TrendingDown, color: "text-red-400", bg: "from-red-600/10 to-transparent", border: "border-red-500/20" },
                    { label: "Resultado neto", value: `${metrics.neto >= 0 ? "+" : ""}${metrics.neto.toLocaleString("es-ES")}€`, icon: Banknote, color: "text-indigo-400", bg: "from-indigo-600/10 to-transparent", border: "border-indigo-500/20" },
                    { label: "Margen", value: `${metrics.margen}%`, icon: Wifi, color: "text-amber-400", bg: "from-amber-600/10 to-transparent", border: "border-amber-500/20" },
                ].map(({ label, value, icon: Icon, color, bg, border }) => (
                    <div key={label} className={`rounded-xl border ${border} bg-gradient-to-br ${bg} bg-[#111113] p-6`}>
                        <div className={`inline-flex p-2 rounded-lg bg-black/20 mb-4`}><Icon className={`w-4 h-4 ${color}`} /></div>
                        <p className={`text-2xl font-bold tabular-nums ${color}`}>{value}</p>
                        <p className="text-xs text-zinc-500 mt-1">{label}</p>
                    </div>
                ))}
            </div>

            {/* Charts row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Donut — Desglose gastos */}
                <div className="rounded-xl border border-[#27272a] bg-[#111113] p-6">
                    <p className="text-sm font-medium text-white mb-5">Desglose de gastos</p>
                    <div className="flex items-center gap-6">
                        <div className="relative flex-shrink-0">
                            <DonutChart segments={categorias} />
                            <div className="absolute inset-0 flex items-center justify-center flex-col">
                                <span className="text-xs text-zinc-400">Total</span>
                                <span className="text-sm font-bold text-white">{totalGastos.toLocaleString("es-ES")}€</span>
                            </div>
                        </div>
                        <div className="flex-1 space-y-2.5">
                            {categorias.map(c => (
                                <div key={c.label}>
                                    <div className="flex justify-between text-xs mb-1">
                                        <span className="text-zinc-400">{c.label}</span>
                                        <span className="text-white tabular-nums">{c.value.toLocaleString("es-ES")}€</span>
                                    </div>
                                    <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
                                        <div className="h-full rounded-full transition-all duration-700"
                                            style={{ width: `${(c.value / totalGastos) * 100}%`, backgroundColor: c.color }} />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Sparkline — Tendencia neta */}
                <div className="rounded-xl border border-[#27272a] bg-[#111113] p-6">
                    <div className="flex items-start justify-between mb-5">
                        <p className="text-sm font-medium text-white">Resultado neto mensual</p>
                        <span className="text-xs text-zinc-500">Últimos 6 meses</span>
                    </div>
                    {mensual.length === 0 ? (
                        <div className="h-[60px] flex items-center justify-center text-sm text-zinc-500">Conecta tu banco para ver la tendencia</div>
                    ) : (
                    <>
                    <BarSparkline values={mensual} color={metrics.neto >= 0 ? "#6366f1" : "#ef4444"} />
                    <div className="flex justify-between mt-2">
                        {["Sep", "Oct", "Nov", "Dic", "Ene", "Feb"].map((m, i) => (
                            <span key={i} className="text-xs text-zinc-600">{m}</span>
                        ))}
                    </div>
                    </>
                    )}
                    {/* Margin gauge */}
                    <div className="mt-6 pt-5 border-t border-[#27272a]">
                        <div className="flex justify-between text-xs mb-2">
                            <span className="text-zinc-400">Margen sobre ingresos</span>
                            <span className="font-bold text-indigo-400">{metrics.margen}%</span>
                        </div>
                        <div className="h-2 rounded-full bg-white/5 overflow-hidden">
                            <div className="h-full rounded-full bg-gradient-to-r from-indigo-600 to-indigo-400 transition-all duration-1000"
                                style={{ width: `${Math.min(100, Math.max(0, metrics.margen))}%` }} />
                        </div>
                        <p className="text-xs text-zinc-600 mt-1.5">
                            {metrics.margen >= 30 ? "✅ Margen saludable" : metrics.margen >= 15 ? "⚠️ Margen ajustado" : "🔴 Margen bajo"}
                        </p>
                    </div>
                </div>
            </div>

            {/* AI summary text */}
            <div className="rounded-xl border border-[#27272a] bg-[#111113] p-6">
                <div className="flex items-center justify-between mb-4">
                    <p className="text-sm font-medium text-white">Análisis del agente IA</p>
                    <button onClick={() => launch("resumen financiero mes")}
                        disabled={status === "polling" || status === "creating"}
                        className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white transition disabled:opacity-50">
                        {status === "polling" || status === "creating" ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
                        {status === "polling" ? "Generando…" : "Regenerar"}
                    </button>
                </div>
                {status === "creating" || status === "polling" ? (
                    <div className="flex items-center gap-3 text-zinc-500 text-sm py-4">
                        <Loader2 className="w-4 h-4 animate-spin" /> El agente está analizando tus finanzas…
                    </div>
                ) : (
                    <p className="text-sm text-zinc-300 leading-relaxed whitespace-pre-line">
                        {resumenTexto ?? "Haz clic en Regenerar para que la IA analice tus movimientos del mes y genere recomendaciones personalizadas."}
                    </p>
                )}
            </div>
        </div>
    );
}
