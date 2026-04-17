"use client";

import { useEffect, useState } from "react";
import { api, type Invoice, type BankTransaction } from "@/lib/api";
import { isPast } from "date-fns";
import { logError } from "@/lib/logger";

export type TabId = "cobros" | "pagos" | "movimientos";

export interface BankSummary {
    ingresos: number;
    gastos: number;
    neto: number;
    margen: number;
    is_demo: boolean;
}

export function usePagosYCobros() {
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [transactions, setTransactions] = useState<BankTransaction[]>([]);
    const [summary, setSummary] = useState<BankSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [syncing, setSyncing] = useState(false);
    const [tab, setTab] = useState<TabId>("cobros");

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

    const sortByDue = (a: Invoice, b: Invoice) => {
        if (!a.due_date) return 1;
        if (!b.due_date) return -1;
        return new Date(a.due_date).getTime() - new Date(b.due_date).getTime();
    };

    const cobros = invoices
        .filter(inv => (inv.invoice_type === "issued" || inv.invoice_type === "emitida" || inv.invoice_type === "venta") && inv.status !== "paid" && inv.status !== "cancelled")
        .sort(sortByDue);

    const pagos = invoices
        .filter(inv => (inv.invoice_type === "received" || inv.invoice_type === "recibida" || inv.invoice_type === "compra") && inv.status !== "paid" && inv.status !== "cancelled")
        .sort(sortByDue);

    const totalCobros = cobros.reduce((s, inv) => s + Number(inv.amount_total), 0);
    const totalPagos = pagos.reduce((s, inv) => s + Number(inv.amount_total), 0);
    const saldoNeto = summary?.neto ?? 0;
    const ultimaTx = transactions[0];
    const saldoCaja = ultimaTx?.balance ?? saldoNeto;
    const overdueCount = [...cobros, ...pagos].filter(inv => inv.due_date && isPast(new Date(inv.due_date))).length;

    return {
        loading, syncing, tab, setTab, transactions,
        cobros, pagos, totalCobros, totalPagos,
        saldoNeto, saldoCaja, ultimaTx, overdueCount,
        handleSync,
    };
}
