"use client";

import { useEffect, useState } from "react";
import { api, type Invoice, type BankTransaction } from "@/lib/api";
import {
    ArrowUpRight, ArrowDownRight, Wallet, RefreshCw,
    Loader2, AlertTriangle, CheckCircle2, Clock, Calendar,
    TrendingUp, TrendingDown, Banknote, ChevronRight
} from "lucide-react";
import { format, differenceInDays, isPast } from "date-fns";
import { es } from "date-fns/locale";
import { cn } from "@/lib/utils";
import { logError } from "@/lib/logger";

const fmt = (v: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(v);

function DueBadge({ dueDate }: { dueDate: string | null }) {
    if (!dueDate) return <span className="text-xs text-zinc-600">Sin vencimiento</span>;
    const d = new Date(dueDate);
    const days = differenceInDays(d, new Date());
    if (isPast(d) && days < 0) {
        return (
            <span className="flex items-center gap-1 text-xs font-medium text-red-400 bg-red-500/10 border border-red-500/20 px-2 py-0.5 rounded-full">
                <AlertTriangle className="w-3 h-3" /> Vencida hace {Math.abs(days)}d
            </span>
        );
    }
    if (days <= 7) {
        return (
            <span className="flex items-center gap-1 text-xs font-medium text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full">
                <Clock className="w-3 h-3" /> {days === 0 ? "Hoy" : `${days}d`}
            </span>
        );
    }
    return (
        <span className="flex items-center gap-1 text-xs text-zinc-400 bg-zinc-800/50 px-2 py-0.5 rounded-full">
            <Calendar className="w-3 h-3" /> {days}d
        </span>
    );
}

export default function PagosYCobrosPage() {
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [transactions, setTransactions] = useState<BankTransaction[]>([]);
    const [summary, setSummary] = useState<{ ingresos: number; gastos: number; neto: number; margen: number; is_demo: boolean } | null>(null);
    const [loading, setLoading] = useState(true);
    const [syncing, setSyncing] = useState(false);
    const [tab, setTab] = useState<"cobros" | "pagos" | "movimientos">("cobros");

    const loadData = async () => {
        setLoading(true);
        try {
            const [inv, txs, sum] = await Promise.all([
                api.erp.invoices.list(),
                api.banking.transactions.list(),
                api.banking.summary(),
            ]);
            setInvoices(inv);
            setTransactions(txs);
            setSummary(sum);
        } catch (e) {
            logError("tesoreria/pagos-y-cobros/page", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { loadData(); }, []);

    const handleSync = async () => {
        setSyncing(true);
        try {
            await api.banking.transactions.sync();
            await loadData();
        } catch { /* ignore */ }
        finally { setSyncing(false); }
    };

    // Facturas pendientes de cobro (emitidas, no pagadas ni canceladas)
    const cobros = invoices
        .filter(inv => (inv.invoice_type === "issued" || inv.invoice_type === "emitida" || inv.invoice_type === "venta") && inv.status !== "paid" && inv.status !== "cancelled")
        .sort((a, b) => {
            if (!a.due_date) return 1;
            if (!b.due_date) return -1;
            return new Date(a.due_date).getTime() - new Date(b.due_date).getTime();
        });

    // Facturas pendientes de pago (recibidas, no pagadas ni canceladas)
    const pagos = invoices
        .filter(inv => (inv.invoice_type === "received" || inv.invoice_type === "recibida" || inv.invoice_type === "compra") && inv.status !== "paid" && inv.status !== "cancelled")
        .sort((a, b) => {
            if (!a.due_date) return 1;
            if (!b.due_date) return -1;
            return new Date(a.due_date).getTime() - new Date(b.due_date).getTime();
        });

    const totalCobros = cobros.reduce((s, inv) => s + Number(inv.amount_total), 0);
    const totalPagos = pagos.reduce((s, inv) => s + Number(inv.amount_total), 0);
    const saldoNeto = (summary?.neto ?? 0);

    // Saldo "caja" = última transacción bancaria si existe, si no, neto de facturas
    const ultimaTx = transactions[0];
    const saldoCaja = ultimaTx?.balance ?? saldoNeto;

    const overdueCount = [...cobros, ...pagos].filter(inv => inv.due_date && isPast(new Date(inv.due_date))).length;

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-white tracking-tight">Pagos y Cobros</h1>
                    <p className="mt-1 text-sm text-zinc-400">Control de liquidez y vencimientos de caja.</p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={handleSync}
                        disabled={syncing}
                        className="flex items-center gap-2 bg-[#18181b] border border-[#3f3f46] hover:bg-zinc-800 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-colors"
                    >
                        {syncing ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                        Sincronizar banco
                    </button>
                </div>
            </div>

            {/* KPIs */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Saldo caja */}
                <div className="bg-[#111113] border border-[#27272a] p-5 rounded-2xl relative overflow-hidden">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="w-9 h-9 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
                            <Wallet className="w-4 h-4 text-blue-400" />
                        </div>
                        <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Caja Actual</span>
                    </div>
                    <p className={cn("text-2xl font-bold tracking-tight", saldoCaja >= 0 ? "text-white" : "text-red-400")}>
                        {loading ? "—" : fmt(saldoCaja)}
                    </p>
                    <p className="text-xs text-zinc-500 mt-1">
                        {ultimaTx ? `Último mov. ${format(new Date(ultimaTx.date), "d MMM", { locale: es })}` : "Sin movimientos bancarios"}
                    </p>
                </div>

                {/* Cobros pendientes */}
                <div className="bg-[#111113] border border-[#27272a] p-5 rounded-2xl">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                            <ArrowUpRight className="w-4 h-4 text-emerald-400" />
                        </div>
                        <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Por Cobrar</span>
                    </div>
                    <p className="text-2xl font-bold text-emerald-400 tracking-tight">
                        {loading ? "—" : fmt(totalCobros)}
                    </p>
                    <p className="text-xs text-zinc-500 mt-1">{cobros.length} factura{cobros.length !== 1 ? "s" : ""} emitida{cobros.length !== 1 ? "s" : ""}</p>
                </div>

                {/* Pagos pendientes */}
                <div className="bg-[#111113] border border-[#27272a] p-5 rounded-2xl">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="w-9 h-9 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
                            <ArrowDownRight className="w-4 h-4 text-red-400" />
                        </div>
                        <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Por Pagar</span>
                    </div>
                    <p className="text-2xl font-bold text-red-400 tracking-tight">
                        {loading ? "—" : fmt(totalPagos)}
                    </p>
                    <p className="text-xs text-zinc-500 mt-1">{pagos.length} factura{pagos.length !== 1 ? "s" : ""} recibida{pagos.length !== 1 ? "s" : ""}</p>
                </div>

                {/* Neto / alerta vencidos */}
                <div className={cn("p-5 rounded-2xl border", overdueCount > 0 ? "bg-red-500/5 border-red-500/20" : "bg-[#111113] border-[#27272a]")}>
                    <div className="flex items-center gap-3 mb-3">
                        <div className={cn("w-9 h-9 rounded-xl flex items-center justify-center", overdueCount > 0 ? "bg-red-500/10 border border-red-500/20" : "bg-zinc-800/80 border border-zinc-700")}>
                            {overdueCount > 0
                                ? <AlertTriangle className="w-4 h-4 text-red-400" />
                                : <TrendingUp className="w-4 h-4 text-zinc-400" />}
                        </div>
                        <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                            {overdueCount > 0 ? "Vencidas" : "Neto periodo"}
                        </span>
                    </div>
                    {overdueCount > 0 ? (
                        <>
                            <p className="text-2xl font-bold text-red-400 tracking-tight">{overdueCount} factura{overdueCount !== 1 ? "s" : ""}</p>
                            <p className="text-xs text-zinc-500 mt-1">Requieren atención inmediata</p>
                        </>
                    ) : (
                        <>
                            <p className={cn("text-2xl font-bold tracking-tight", saldoNeto >= 0 ? "text-white" : "text-red-400")}>
                                {loading ? "—" : fmt(saldoNeto)}
                            </p>
                            <p className="text-xs text-zinc-500 mt-1">Ingresos − gastos acumulados</p>
                        </>
                    )}
                </div>
            </div>

            {/* Tabs + Tabla */}
            <div className="bg-[#111113] border border-[#27272a] rounded-2xl overflow-hidden">
                {/* Tab bar */}
                <div className="flex border-b border-[#27272a] bg-[#161618]">
                    {([
                        { id: "cobros", label: `Cobros pendientes (${cobros.length})`, color: "text-emerald-400", active: "border-emerald-500" },
                        { id: "pagos", label: `Pagos pendientes (${pagos.length})`, color: "text-red-400", active: "border-red-500" },
                        { id: "movimientos", label: `Movimientos bancarios (${transactions.length})`, color: "text-blue-400", active: "border-blue-500" },
                    ] as const).map(t => (
                        <button
                            key={t.id}
                            onClick={() => setTab(t.id)}
                            className={cn(
                                "px-5 py-3.5 text-sm font-medium border-b-2 transition-colors",
                                tab === t.id ? `${t.color} ${t.active}` : "text-zinc-500 border-transparent hover:text-zinc-300"
                            )}
                        >
                            {t.label}
                        </button>
                    ))}
                </div>

                {/* Contenido */}
                {loading ? (
                    <div className="py-16 flex items-center justify-center">
                        <Loader2 className="w-6 h-6 text-zinc-500 animate-spin" />
                    </div>
                ) : (

                    /* ── COBROS ─────────────────────────────────────────── */
                    tab === "cobros" ? (
                        cobros.length === 0 ? (
                            <div className="py-16 text-center">
                                <CheckCircle2 className="w-10 h-10 text-emerald-600 mx-auto mb-3" />
                                <p className="text-zinc-400 font-medium">Sin cobros pendientes</p>
                                <p className="text-xs text-zinc-600 mt-1">Todas las facturas emitidas están pagadas.</p>
                            </div>
                        ) : (
                            <table className="w-full text-left text-sm">
                                <thead className="bg-[#161618]/50 text-zinc-400 border-b border-[#27272a]">
                                    <tr>
                                        <th className="px-6 py-3 font-medium">Nº Factura</th>
                                        <th className="px-6 py-3 font-medium">Cliente</th>
                                        <th className="px-6 py-3 font-medium text-right">Importe</th>
                                        <th className="px-6 py-3 font-medium">Vencimiento</th>
                                        <th className="px-6 py-3 font-medium">Estado</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-[#27272a]/50">
                                    {cobros.map(inv => (
                                        <tr key={inv.id} className="hover:bg-emerald-500/[0.02] transition-colors">
                                            <td className="px-6 py-4 font-mono text-xs text-zinc-400">{inv.invoice_number || inv.id.slice(0, 8)}</td>
                                            <td className="px-6 py-4 text-white font-medium">{inv.client?.name || "—"}</td>
                                            <td className="px-6 py-4 text-right font-semibold text-emerald-400">{fmt(Number(inv.amount_total))}</td>
                                            <td className="px-6 py-4">
                                                {inv.due_date ? (
                                                    <span className="text-xs text-zinc-300">{format(new Date(inv.due_date), "d MMM yyyy", { locale: es })}</span>
                                                ) : <span className="text-xs text-zinc-600">—</span>}
                                            </td>
                                            <td className="px-6 py-4"><DueBadge dueDate={inv.due_date} /></td>
                                        </tr>
                                    ))}
                                </tbody>
                                <tfoot className="border-t border-[#27272a] bg-[#161618]/30">
                                    <tr>
                                        <td colSpan={2} className="px-6 py-3 text-sm font-semibold text-zinc-300">Total</td>
                                        <td className="px-6 py-3 text-right font-bold text-emerald-400">{fmt(totalCobros)}</td>
                                        <td colSpan={2} />
                                    </tr>
                                </tfoot>
                            </table>
                        )
                    )

                    /* ── PAGOS ──────────────────────────────────────────── */
                    : tab === "pagos" ? (
                        pagos.length === 0 ? (
                            <div className="py-16 text-center">
                                <CheckCircle2 className="w-10 h-10 text-emerald-600 mx-auto mb-3" />
                                <p className="text-zinc-400 font-medium">Sin pagos pendientes</p>
                                <p className="text-xs text-zinc-600 mt-1">Todas las facturas recibidas están pagadas.</p>
                            </div>
                        ) : (
                            <table className="w-full text-left text-sm">
                                <thead className="bg-[#161618]/50 text-zinc-400 border-b border-[#27272a]">
                                    <tr>
                                        <th className="px-6 py-3 font-medium">Nº Factura</th>
                                        <th className="px-6 py-3 font-medium">Proveedor</th>
                                        <th className="px-6 py-3 font-medium text-right">Importe</th>
                                        <th className="px-6 py-3 font-medium">Vencimiento</th>
                                        <th className="px-6 py-3 font-medium">Estado</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-[#27272a]/50">
                                    {pagos.map(inv => (
                                        <tr key={inv.id} className="hover:bg-red-500/[0.02] transition-colors">
                                            <td className="px-6 py-4 font-mono text-xs text-zinc-400">{inv.invoice_number || inv.id.slice(0, 8)}</td>
                                            <td className="px-6 py-4 text-white font-medium">{inv.client?.name || "—"}</td>
                                            <td className="px-6 py-4 text-right font-semibold text-red-400">{fmt(Number(inv.amount_total))}</td>
                                            <td className="px-6 py-4">
                                                {inv.due_date ? (
                                                    <span className="text-xs text-zinc-300">{format(new Date(inv.due_date), "d MMM yyyy", { locale: es })}</span>
                                                ) : <span className="text-xs text-zinc-600">—</span>}
                                            </td>
                                            <td className="px-6 py-4"><DueBadge dueDate={inv.due_date} /></td>
                                        </tr>
                                    ))}
                                </tbody>
                                <tfoot className="border-t border-[#27272a] bg-[#161618]/30">
                                    <tr>
                                        <td colSpan={2} className="px-6 py-3 text-sm font-semibold text-zinc-300">Total</td>
                                        <td className="px-6 py-3 text-right font-bold text-red-400">{fmt(totalPagos)}</td>
                                        <td colSpan={2} />
                                    </tr>
                                </tfoot>
                            </table>
                        )
                    )

                    /* ── MOVIMIENTOS ────────────────────────────────────── */
                    : (
                        transactions.length === 0 ? (
                            <div className="py-16 text-center">
                                <Banknote className="w-10 h-10 text-zinc-600 mx-auto mb-3" />
                                <p className="text-zinc-400 font-medium">Sin movimientos bancarios</p>
                                <p className="text-xs text-zinc-600 mt-1">Pulsa &ldquo;Sincronizar banco&rdquo; para importar movimientos.</p>
                                <button onClick={handleSync} disabled={syncing} className="mt-4 flex items-center gap-2 mx-auto px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-xl transition-colors">
                                    {syncing ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                                    Sincronizar ahora
                                </button>
                            </div>
                        ) : (
                            <table className="w-full text-left text-sm">
                                <thead className="bg-[#161618]/50 text-zinc-400 border-b border-[#27272a]">
                                    <tr>
                                        <th className="px-6 py-3 font-medium">Fecha</th>
                                        <th className="px-6 py-3 font-medium">Concepto</th>
                                        <th className="px-6 py-3 font-medium text-right">Importe</th>
                                        <th className="px-6 py-3 font-medium text-right">Saldo</th>
                                        <th className="px-6 py-3 font-medium">Estado</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-[#27272a]/50">
                                    {transactions.map(tx => (
                                        <tr key={tx.id} className="hover:bg-blue-500/[0.02] transition-colors">
                                            <td className="px-6 py-4 text-xs text-zinc-400 whitespace-nowrap">
                                                {format(new Date(tx.date), "d MMM yyyy", { locale: es })}
                                            </td>
                                            <td className="px-6 py-4 text-white">{tx.description}</td>
                                            <td className={cn("px-6 py-4 text-right font-semibold", tx.amount >= 0 ? "text-emerald-400" : "text-red-400")}>
                                                {tx.amount >= 0 ? "+" : ""}{fmt(tx.amount)}
                                            </td>
                                            <td className="px-6 py-4 text-right text-zinc-300 text-xs">
                                                {tx.balance != null ? fmt(tx.balance) : "—"}
                                            </td>
                                            <td className="px-6 py-4">
                                                {tx.status === "reconciled" ? (
                                                    <span className="flex items-center gap-1 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                                                        <CheckCircle2 className="w-3 h-3" /> Conciliado
                                                    </span>
                                                ) : (
                                                    <span className="flex items-center gap-1 text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full">
                                                        <Clock className="w-3 h-3" /> Pendiente
                                                    </span>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )
                    )
                )}
            </div>

            {/* Footer info */}
            <div className="flex items-center gap-2 text-xs text-zinc-600">
                <TrendingDown className="w-3.5 h-3.5" />
                Los importes de cobros y pagos provienen de facturas emitidas y recibidas no cobradas/pagadas.
                Los movimientos bancarios son importados via sincronización PSD2.
            </div>
        </div>
    );
}
