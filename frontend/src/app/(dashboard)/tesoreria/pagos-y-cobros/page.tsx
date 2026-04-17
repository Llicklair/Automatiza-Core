"use client";

import { RefreshCw, Loader2, TrendingDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { usePagosYCobros } from "./_hooks/usePagosYCobros";
import KpiCards from "./_components/KpiCards";
import InvoiceTable from "./_components/InvoiceTable";
import TransactionsTable from "./_components/TransactionsTable";

export default function PagosYCobrosPage() {
    const {
        loading, syncing, tab, setTab, transactions,
        cobros, pagos, totalCobros, totalPagos,
        saldoNeto, saldoCaja, ultimaTx, overdueCount,
        handleSync,
    } = usePagosYCobros();

    const tabs = [
        { id: "cobros", label: `Cobros pendientes (${cobros.length})`, color: "text-emerald-400", active: "border-emerald-500" },
        { id: "pagos", label: `Pagos pendientes (${pagos.length})`, color: "text-red-400", active: "border-red-500" },
        { id: "movimientos", label: `Movimientos bancarios (${transactions.length})`, color: "text-blue-400", active: "border-blue-500" },
    ] as const;

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-foreground tracking-tight">Pagos y Cobros</h1>
                    <p className="mt-1 text-sm text-muted-foreground">Control de liquidez y vencimientos de caja.</p>
                </div>
                <button onClick={handleSync} disabled={syncing}
                    className="flex items-center gap-2 bg-card border border-border hover:bg-muted text-foreground px-4 py-2.5 rounded-xl text-sm font-medium transition-colors">
                    {syncing ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                    Sincronizar banco
                </button>
            </div>

            <KpiCards loading={loading} saldoCaja={saldoCaja} ultimaTx={ultimaTx}
                totalCobros={totalCobros} cobrosCount={cobros.length}
                totalPagos={totalPagos} pagosCount={pagos.length}
                overdueCount={overdueCount} saldoNeto={saldoNeto} />

            {/* Tabs + Table */}
            <div className="bg-card border border-border rounded-2xl overflow-hidden">
                <div className="flex border-b border-border bg-muted">
                    {tabs.map(t => (
                        <button key={t.id} onClick={() => setTab(t.id)}
                            className={cn("px-5 py-3.5 text-sm font-medium border-b-2 transition-colors",
                                tab === t.id ? `${t.color} ${t.active}` : "text-muted-foreground border-transparent hover:text-foreground")}>
                            {t.label}
                        </button>
                    ))}
                </div>

                {loading ? (
                    <div className="py-16 flex items-center justify-center">
                        <Loader2 className="w-6 h-6 text-muted-foreground animate-spin" />
                    </div>
                ) : tab === "cobros" ? (
                    <InvoiceTable items={cobros} total={totalCobros} variant="cobros" />
                ) : tab === "pagos" ? (
                    <InvoiceTable items={pagos} total={totalPagos} variant="pagos" />
                ) : (
                    <TransactionsTable transactions={transactions} syncing={syncing} onSync={handleSync} />
                )}
            </div>

            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <TrendingDown className="w-3.5 h-3.5" />
                Los importes de cobros y pagos provienen de facturas emitidas y recibidas no cobradas/pagadas.
                Los movimientos bancarios son importados via sincronizacion PSD2.
            </div>
        </div>
    );
}
