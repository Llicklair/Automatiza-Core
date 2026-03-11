"use client";

import { useEffect, useState } from "react";
import { api, type Invoice, type Payroll } from "@/lib/api";
import { AreaChart, Wallet, ArrowUpRight, ArrowDownRight, CalendarDays, Filter } from "lucide-react";
import { cn } from "@/lib/utils";

export default function CashflowPage() {
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [payrolls, setPayrolls] = useState<Payroll[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<'all' | 'in' | 'out'>('all');

    const loadData = async () => {
        setLoading(true);
        try {
            // Cargar facturas (ingresos/gastos) y nóminas (gastos)
            const [inv, pay] = await Promise.all([
                api.erp.invoices.list(),
                api.hr.payrolls.list()
            ]);
            setInvoices(inv);
            setPayrolls(pay);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { loadData(); }, []);

    // Construir la línea de tiempo del Cashflow unificando entidades
    const timelineEvents: { date: Date; type: 'in' | 'out'; amount: number; description: string; ref: string }[] = [];

    invoices.forEach(inv => {
        if (inv.status === 'draft' || inv.status === 'cancelled') return;

        // Ventas suman (in), Compras restan (out)
        const isIncome = inv.invoice_type === 'emitida' || inv.invoice_type === 'venta';
        const dateObj = new Date(inv.due_date || inv.date); // Usar vencimiento si existe

        timelineEvents.push({
            date: dateObj,
            type: isIncome ? 'in' : 'out',
            amount: Number(inv.amount_total) || 0,
            description: `Factura ${inv.client?.name || 'Cliente'}`,
            ref: inv.invoice_number || inv.id.substring(0, 8)
        });
    });

    payrolls.forEach(pay => {
        // Las nóminas siempre restan
        timelineEvents.push({
            date: new Date(pay.issue_date),
            type: 'out',
            amount: Number(pay.net_salary) || 0,
            description: `Nómina ${pay.employee?.name || 'Empleado'}`,
            ref: `PAY-${pay.id.substring(0, 5).toUpperCase()}`
        });
    });

    // Ordenar cronológicamente (más antiguo a más reciente)
    timelineEvents.sort((a, b) => a.date.getTime() - b.date.getTime());

    // Calcular KPIs
    const totalIn = timelineEvents.filter(e => e.type === 'in').reduce((acc, curr) => acc + curr.amount, 0);
    const totalOut = timelineEvents.filter(e => e.type === 'out').reduce((acc, curr) => acc + curr.amount, 0);
    const netFlow = totalIn - totalOut;

    // Filtrar para la vista
    const visibleEvents = timelineEvents.filter(e => filter === 'all' || e.type === filter)
        .sort((a, b) => b.date.getTime() - a.date.getTime()); // Invertir orden para ver lo reciente primero

    return (
        <div className="p-8 max-w-5xl mx-auto space-y-8 animate-in fade-in duration-500">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold text-white mb-2">Previsión de Tesorería (Cashflow)</h1>
                <p className="text-zinc-400">Analiza tus cobros y pagos futuros basados en facturas de venta, compra y nóminas.</p>
            </div>

            {/* Cajas de resumen */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-6 relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                        <ArrowUpRight className="w-24 h-24 text-emerald-500" />
                    </div>
                    <div className="relative z-10">
                        <p className="text-sm font-medium text-zinc-400 mb-1">Entradas Previstas</p>
                        <p className="text-3xl font-bold text-emerald-400">
                            {totalIn.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}
                        </p>
                    </div>
                </div>

                <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-6 relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                        <ArrowDownRight className="w-24 h-24 text-rose-500" />
                    </div>
                    <div className="relative z-10">
                        <p className="text-sm font-medium text-zinc-400 mb-1">Salidas Previstas</p>
                        <p className="text-3xl font-bold text-rose-400">
                            {totalOut.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}
                        </p>
                    </div>
                </div>

                <div className={cn("border rounded-2xl p-6 relative overflow-hidden", netFlow >= 0 ? "bg-emerald-500/10 border-emerald-500/20" : "bg-rose-500/10 border-rose-500/20")}>
                    <div className="absolute top-0 right-0 p-4 opacity-20">
                        <Wallet className={cn("w-24 h-24", netFlow >= 0 ? "text-emerald-500" : "text-rose-500")} />
                    </div>
                    <div className="relative z-10">
                        <p className={cn("text-sm font-medium mb-1", netFlow >= 0 ? "text-emerald-400/80" : "text-rose-400/80")}>Flujo de Caja Neto</p>
                        <p className={cn("text-3xl font-bold", netFlow >= 0 ? "text-emerald-400" : "text-rose-400")}>
                            {netFlow.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}
                        </p>
                    </div>
                </div>
            </div>

            {/* Línea de tiempo */}
            <div className="bg-[#111113] border border-[#27272a] rounded-2xl overflow-hidden shadow-2xl flex flex-col">
                <div className="p-4 border-b border-[#27272a] flex items-center justify-between bg-[#18181b]">
                    <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                        <AreaChart className="w-5 h-5 text-indigo-400" />
                        Histórico de Movimientos
                    </h3>

                    <div className="flex bg-black/40 rounded-lg p-1 border border-white/5">
                        <button onClick={() => setFilter('all')} className={cn("px-3 py-1.5 rounded-md text-xs font-medium transition-colors", filter === 'all' ? "bg-zinc-800 text-white shadow-sm" : "text-zinc-400 hover:text-white hover:bg-white/5")}>Todos</button>
                        <button onClick={() => setFilter('in')} className={cn("px-3 py-1.5 rounded-md text-xs font-medium transition-colors", filter === 'in' ? "bg-emerald-500/20 text-emerald-400 shadow-sm" : "text-zinc-400 hover:text-emerald-400 hover:bg-white/5")}>Entradas</button>
                        <button onClick={() => setFilter('out')} className={cn("px-3 py-1.5 rounded-md text-xs font-medium transition-colors", filter === 'out' ? "bg-rose-500/20 text-rose-400 shadow-sm" : "text-zinc-400 hover:text-rose-400 hover:bg-white/5")}>Salidas</button>
                    </div>
                </div>

                {loading ? (
                    <div className="p-16 text-center text-zinc-500 animate-pulse">Analizando flujos...</div>
                ) : visibleEvents.length === 0 ? (
                    <div className="p-16 text-center">
                        <CalendarDays className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
                        <p className="text-zinc-400">No hay movimientos financieros previstos.</p>
                    </div>
                ) : (
                    <div className="divide-y divide-[#27272a] max-h-[600px] overflow-y-auto custom-scrollbar">
                        {visibleEvents.map((evt, idx) => (
                            <div key={idx} className="p-4 flex items-center gap-4 hover:bg-white/[0.02] transition-colors">
                                <div className={cn("w-10 h-10 rounded-full flex items-center justify-center shrink-0 border",
                                    evt.type === 'in' ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-500" : "bg-rose-500/10 border-rose-500/20 text-rose-500")}>
                                    {evt.type === 'in' ? <ArrowUpRight className="w-5 h-5" /> : <ArrowDownRight className="w-5 h-5" />}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-1">
                                        <p className="font-semibold text-white truncate">{evt.description}</p>
                                        <span className="text-xs bg-black/40 text-zinc-400 px-2 py-0.5 rounded font-mono">{evt.ref}</span>
                                    </div>
                                    <div className="flex items-center gap-4 text-xs text-zinc-500">
                                        <span className="flex items-center gap-1.5">
                                            <CalendarDays className="w-3.5 h-3.5" />
                                            {evt.date.toLocaleDateString('es-ES', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' })}
                                        </span>
                                    </div>
                                </div>
                                <div className={cn("font-bold text-lg whitespace-nowrap", evt.type === 'in' ? "text-emerald-400" : "text-rose-400")}>
                                    {evt.type === 'in' ? '+' : '-'}{evt.amount.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
