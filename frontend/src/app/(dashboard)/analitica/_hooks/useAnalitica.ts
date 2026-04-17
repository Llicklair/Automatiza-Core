"use client";

import { useEffect, useState } from "react";
import { api, type Invoice, type Task } from "@/lib/api";

interface CashflowEntry {
    month: string;
    ingresos: number;
    gastos: number;
}

interface BankingAnalyticsResponse {
    cashflow: CashflowEntry[];
    insights: unknown[];
}

export type { CashflowEntry };

export function useAnalitica() {
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [tasks, setTasks] = useState<Task[]>([]);
    const [cashflow, setCashflow] = useState<CashflowEntry[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        Promise.all([
            api.erp.invoices.list({ limit: 200 }).catch(() => []),
            api.tasks.list({ limit: 100 }).catch(() => []),
            api.banking.analytics().catch(() => ({ cashflow: [], insights: [] })),
        ]).then(([inv, tsk, analytics]) => {
            setInvoices(inv);
            setTasks(tsk);
            setCashflow((analytics as BankingAnalyticsResponse).cashflow || []);
        }).finally(() => setLoading(false));
    }, []);

    const emitidas = invoices.filter(i => i.invoice_type === "issued");
    const recibidas = invoices.filter(i => i.invoice_type === "received");

    const totalIngresos = emitidas.reduce((s, i) => s + Number(i.amount_total), 0);
    const totalGastos = recibidas.reduce((s, i) => s + Number(i.amount_total), 0);
    const beneficio = totalIngresos - totalGastos;
    const margen = totalIngresos > 0 ? Math.round((beneficio / totalIngresos) * 100) : 0;

    const factPagadas = emitidas.filter(i => i.status === "paid").length;
    const factPendientes = emitidas.filter(i => i.status === "pending").length;
    const factBorrador = emitidas.filter(i => i.status === "draft").length;

    const clientMap: Record<string, number> = {};
    emitidas.forEach(inv => {
        const name = inv.client?.name || "Desconocido";
        clientMap[name] = (clientMap[name] || 0) + Number(inv.amount_total);
    });
    const topClientes = Object.entries(clientMap)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5)
        .map(([name, total]) => ({ name, total }));

    const pieData = [
        { name: "Cobradas", value: emitidas.filter(i => i.status === "paid").reduce((s, i) => s + Number(i.amount_total), 0) },
        { name: "Pendientes", value: emitidas.filter(i => i.status === "pending").reduce((s, i) => s + Number(i.amount_total), 0) },
        { name: "Borradores", value: emitidas.filter(i => i.status === "draft").reduce((s, i) => s + Number(i.amount_total), 0) },
    ].filter(d => d.value > 0);

    const tasksDone = tasks.filter(t => t.status === "done").length;
    const tasksFailed = tasks.filter(t => t.status === "failed").length;
    const tasksTotal = tasks.length;
    const tasksSuccessRate = tasksTotal > 0 ? Math.round((tasksDone / tasksTotal) * 100) : 0;
    const tasksPending = tasks.filter(t => t.status === "pending" || t.status === "executing").length;

    const isDemo = invoices.length === 0;

    return {
        loading, cashflow, isDemo,
        totalIngresos, totalGastos, beneficio, margen,
        emitidas, recibidas,
        factPagadas, factPendientes, factBorrador,
        topClientes, pieData,
        tasksDone, tasksFailed, tasksSuccessRate, tasksPending,
    };
}
