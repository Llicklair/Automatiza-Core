"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowDownLeft, ArrowUpRight, Banknote, FileDown, FileUp, Loader2, RefreshCw, TrendingDown, TrendingUp } from "lucide-react";
import { ColumnDef } from "@tanstack/react-table";
import { api, type BankTransaction, type Invoice } from "@/lib/api";
import { DataTable, DataTableColumnHeader } from "@/components/data-table";
import { KpiCard } from "@/components/shared/KpiCard";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useToastStore } from "@/stores/toast";
import { logError } from "@/lib/logger";

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

export function TransaccionesTab() {
    const toast = useToastStore();
    const [txList, setTxList] = useState<BankTransaction[]>([]);
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [isSyncing, setIsSyncing] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [dateFrom, setDateFrom] = useState("");
    const [dateTo, setDateTo] = useState("");
    const [reconcileTx, setReconcileTx] = useState<BankTransaction | null>(null);
    const [selectedInvoice, setSelectedInvoice] = useState("");
    const [reconciling, setReconciling] = useState(false);
    const [importingN43, setImportingN43] = useState(false);
    const n43InputRef = useRef<HTMLInputElement>(null);

    useEffect(() => { loadData(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

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

    const handleImportN43 = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        e.target.value = "";
        if (!file) return;
        setImportingN43(true);
        try {
            const res = await api.banking.transactions.importN43(file);
            toast.success(
                `Extracto importado: ${res.imported} nuevos, ${res.skipped} duplicados, ${res.reconciled} conciliados`
            );
            if (res.errors.length > 0) {
                toast.error(`${res.errors.length} movimientos con errores`);
            }
            await loadData();
        } catch (error) {
            logError("banca/import-n43", error);
            toast.error(error instanceof Error ? error.message : "Error al importar el fichero N43.");
        } finally {
            setImportingN43(false);
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
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <KpiCard title="Ingresos" value={`+${ingresos.toLocaleString("es-ES", { minimumFractionDigits: 2 })}€`} icon={TrendingUp} />
                <KpiCard title="Gastos" value={`-${gastos.toLocaleString("es-ES", { minimumFractionDigits: 2 })}€`} icon={TrendingDown} />
                <KpiCard title="Neto" value={`${ingresos - gastos >= 0 ? "+" : ""}${(ingresos - gastos).toLocaleString("es-ES", { minimumFractionDigits: 2 })}€`} icon={Banknote} />
            </div>

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
                    <input
                        ref={n43InputRef}
                        type="file"
                        accept=".n43,.txt,.aeb,.q43"
                        className="hidden"
                        onChange={handleImportN43}
                    />
                    <Button size="sm" variant="outline" onClick={() => n43InputRef.current?.click()} disabled={importingN43} title="Importar extracto bancario Norma 43 (AEB)">
                        {importingN43 ? <Loader2 className="mr-2 h-3 w-3 animate-spin" /> : <FileUp className="mr-2 h-3 w-3" />}
                        {importingN43 ? "Importando…" : "Importar N43"}
                    </Button>
                    <Button size="sm" variant="outline" onClick={exportCsv} disabled={filteredTx.length === 0}>
                        <FileDown className="mr-2 h-3 w-3" /> Exportar CSV
                    </Button>
                    <Button size="sm" onClick={handleSync} disabled={isSyncing}>
                        {isSyncing ? <Loader2 className="mr-2 h-3 w-3 animate-spin" /> : <RefreshCw className="mr-2 h-3 w-3" />}
                        {isSyncing ? "Sincronizando…" : "Descargar movimientos"}
                    </Button>
                </div>
            </div>

            <DataTable
                columns={columns}
                data={filteredTx}
                isLoading={isLoading}
                searchKey="description"
                searchPlaceholder="Buscar por concepto…"
                emptyMessage="Pulsa en 'Descargar movimientos' para importar desde tu banco."
                facetedFilters={[
                    { column: "status", title: "Estado", options: [
                        { label: "Pendiente", value: "pending" },
                        { label: "Conciliada", value: "reconciled" },
                    ]},
                ]}
            />

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
