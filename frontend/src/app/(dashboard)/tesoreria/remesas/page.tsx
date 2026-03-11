"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { api, type Invoice, type Payroll, type Task } from "@/lib/api";
import {
    FileText, Send, Download, CheckCircle2, Clock,
    Loader2, AlertCircle, X, Plus, ChevronDown, ChevronUp,
    Building2, WalletCards
} from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { cn } from "@/lib/utils";

const fmt = (v: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(v);

type RemesaType = "cobros" | "pagos" | "nominas";

interface RemesaItem {
    id: string;
    type: RemesaType;
    label: string;
    sublabel: string;
    amount: number;
    date: string;
    selected: boolean;
}

function useAgentTask() {
    const [status, setStatus] = useState<"idle" | "creating" | "polling" | "done" | "failed">("idle");
    const [error, setError] = useState<string | null>(null);
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const stop = useCallback(() => {
        if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }
    }, []);

    const launch = useCallback(async (intent: string) => {
        stop(); setError(null); setStatus("creating");
        try {
            const task = await api.tasks.create("banking", intent);
            setStatus("polling");
            intervalRef.current = setInterval(async () => {
                try {
                    const t: Task = await api.tasks.get(task.id);
                    if (t.status === "done" || t.status === "failed" || t.status === "cancelled") {
                        stop();
                        setStatus(t.status === "done" ? "done" : "failed");
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
    return { launch, status, error, reset: () => { stop(); setStatus("idle"); setError(null); } };
}

export default function RemesasPage() {
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [payrolls, setPayrolls] = useState<Payroll[]>([]);
    const [loading, setLoading] = useState(true);
    const [items, setItems] = useState<RemesaItem[]>([]);
    const [activeType, setActiveType] = useState<RemesaType>("pagos");
    const [showModal, setShowModal] = useState(false);
    const [toast, setToast] = useState<{ msg: string; type: "ok" | "err" } | null>(null);
    const agent = useAgentTask();

    const showToast = (msg: string, type: "ok" | "err") => {
        setToast({ msg, type });
        setTimeout(() => setToast(null), 5000);
    };

    const loadData = async () => {
        setLoading(true);
        try {
            const [inv, pay] = await Promise.all([
                api.erp.invoices.list(),
                api.hr.payrolls.list(),
            ]);
            setInvoices(inv);
            setPayrolls(pay);

            const newItems: RemesaItem[] = [];

            // Cobros: facturas emitidas pendientes
            inv.filter(i => (i.invoice_type === "issued" || i.invoice_type === "emitida" || i.invoice_type === "venta") && i.status === "pending")
                .forEach(i => newItems.push({
                    id: i.id, type: "cobros",
                    label: i.client?.name || `Factura ${i.invoice_number || i.id.slice(0, 6)}`,
                    sublabel: `Fac. ${i.invoice_number || i.id.slice(0, 8)}`,
                    amount: Number(i.amount_total),
                    date: i.due_date || i.date,
                    selected: false,
                }));

            // Pagos: facturas recibidas pendientes
            inv.filter(i => (i.invoice_type === "received" || i.invoice_type === "recibida" || i.invoice_type === "compra") && i.status !== "paid" && i.status !== "cancelled")
                .forEach(i => newItems.push({
                    id: i.id, type: "pagos",
                    label: i.client?.name || `Proveedor`,
                    sublabel: `Fac. ${i.invoice_number || i.id.slice(0, 8)}`,
                    amount: Number(i.amount_total),
                    date: i.due_date || i.date,
                    selected: false,
                }));

            // Nóminas emitidas
            pay.filter(p => p.status === "sent")
                .forEach(p => newItems.push({
                    id: p.id, type: "nominas",
                    label: p.employee?.name || "Empleado",
                    sublabel: `Nómina ${format(new Date(p.period_start), "MMM yyyy", { locale: es })}`,
                    amount: Number(p.net_salary),
                    date: p.period_end,
                    selected: false,
                }));

            setItems(newItems);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { loadData(); }, []);

    const filtered = items.filter(i => i.type === activeType);
    const selected = items.filter(i => i.selected);
    const totalSelected = selected.reduce((s, i) => s + i.amount, 0);

    const toggle = (id: string) =>
        setItems(prev => prev.map(i => i.id === id ? { ...i, selected: !i.selected } : i));

    const selectAll = () =>
        setItems(prev => prev.map(i => i.type === activeType ? { ...i, selected: true } : i));

    const deselectAll = () =>
        setItems(prev => prev.map(i => i.type === activeType ? { ...i, selected: false } : i));

    const handleGenerar = async () => {
        if (selected.length === 0) return;
        const cobrosItems = selected.filter(i => i.type === "cobros");
        const pagosItems = selected.filter(i => i.type === "pagos");
        const nominasItems = selected.filter(i => i.type === "nominas");

        let intent = `Genera un fichero de remesa SEPA para el banco con los siguientes conceptos:\n`;
        if (cobrosItems.length) intent += `- Cobros (SEPA B2B) por ${fmt(cobrosItems.reduce((s, i) => s + i.amount, 0))} de ${cobrosItems.length} factura(s) emitida(s): ${cobrosItems.map(i => i.sublabel).join(", ")}.\n`;
        if (pagosItems.length) intent += `- Pagos a proveedores por ${fmt(pagosItems.reduce((s, i) => s + i.amount, 0))} de ${pagosItems.length} factura(s) recibida(s): ${pagosItems.map(i => i.label).join(", ")}.\n`;
        if (nominasItems.length) intent += `- Transferencias de nóminas por ${fmt(nominasItems.reduce((s, i) => s + i.amount, 0))} para ${nominasItems.map(i => i.label).join(", ")}.\n`;
        intent += `Total remesa: ${fmt(totalSelected)}. Genera el XML SEPA y registra la operación.`;

        await agent.launch(intent);
        setShowModal(true);
    };

    const typeConfig = {
        cobros: { label: "Cobros (B2B)", color: "text-emerald-400", border: "border-emerald-500", bg: "bg-emerald-500/10" },
        pagos: { label: "Pagos a proveedores", color: "text-red-400", border: "border-red-500", bg: "bg-red-500/10" },
        nominas: { label: "Transferencias nóminas", color: "text-blue-400", border: "border-blue-500", bg: "bg-blue-500/10" },
    };

    return (
        <div className="p-8 max-w-6xl mx-auto space-y-8 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-white tracking-tight">Remesas Bancarias SEPA</h1>
                    <p className="mt-1 text-sm text-zinc-400">
                        Agrupa facturas y nóminas para generar ficheros SEPA XML listos para tu banco.
                    </p>
                </div>
                <button
                    onClick={handleGenerar}
                    disabled={selected.length === 0 || agent.status === "creating" || agent.status === "polling"}
                    className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white px-5 py-2.5 rounded-xl font-medium transition-colors text-sm shadow-lg shadow-indigo-500/20"
                >
                    {(agent.status === "creating" || agent.status === "polling")
                        ? <Loader2 className="w-4 h-4 animate-spin" />
                        : <Send className="w-4 h-4" />}
                    {selected.length > 0 ? `Generar remesa (${fmt(totalSelected)})` : "Selecciona conceptos"}
                </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Panel izquierdo: selección */}
                <div className="lg:col-span-2 space-y-4">
                    {/* Tabs tipo */}
                    <div className="flex gap-2">
                        {(["pagos", "cobros", "nominas"] as RemesaType[]).map(t => {
                            const c = typeConfig[t];
                            const count = items.filter(i => i.type === t).length;
                            return (
                                <button
                                    key={t}
                                    onClick={() => setActiveType(t)}
                                    className={cn(
                                        "px-4 py-2 rounded-xl text-sm font-medium border transition-all",
                                        activeType === t ? `${c.color} ${c.border} ${c.bg}` : "text-zinc-400 border-[#27272a] hover:text-zinc-200 hover:border-zinc-600"
                                    )}
                                >
                                    {c.label} ({count})
                                </button>
                            );
                        })}
                    </div>

                    {/* Lista */}
                    <div className="bg-[#111113] border border-[#27272a] rounded-2xl overflow-hidden">
                        {/* Toolbar */}
                        <div className="px-5 py-3 border-b border-[#27272a] flex items-center justify-between bg-[#161618]">
                            <span className="text-sm text-zinc-400">
                                {filtered.filter(i => i.selected).length} de {filtered.length} seleccionados
                            </span>
                            <div className="flex gap-3 text-xs">
                                <button onClick={selectAll} className="text-indigo-400 hover:text-indigo-300 transition-colors">Seleccionar todo</button>
                                <span className="text-zinc-700">|</span>
                                <button onClick={deselectAll} className="text-zinc-500 hover:text-zinc-300 transition-colors">Ninguno</button>
                            </div>
                        </div>

                        {loading ? (
                            <div className="py-12 flex items-center justify-center">
                                <Loader2 className="w-5 h-5 animate-spin text-zinc-500" />
                            </div>
                        ) : filtered.length === 0 ? (
                            <div className="py-12 text-center">
                                {activeType === "cobros" && <FileText className="w-10 h-10 text-zinc-700 mx-auto mb-3" />}
                                {activeType === "pagos" && <Building2 className="w-10 h-10 text-zinc-700 mx-auto mb-3" />}
                                {activeType === "nominas" && <WalletCards className="w-10 h-10 text-zinc-700 mx-auto mb-3" />}
                                <p className="text-zinc-500 text-sm">
                                    {activeType === "cobros" && "No hay facturas emitidas pendientes de cobro"}
                                    {activeType === "pagos" && "No hay facturas recibidas pendientes de pago"}
                                    {activeType === "nominas" && "No hay nóminas emitidas pendientes de transferencia"}
                                </p>
                            </div>
                        ) : (
                            <div className="divide-y divide-[#27272a]/50">
                                {filtered.map(item => (
                                    <label
                                        key={item.id}
                                        className={cn(
                                            "flex items-center gap-4 px-5 py-4 cursor-pointer transition-colors",
                                            item.selected ? "bg-indigo-500/5" : "hover:bg-white/[0.02]"
                                        )}
                                    >
                                        <input
                                            type="checkbox"
                                            checked={item.selected}
                                            onChange={() => toggle(item.id)}
                                            className="w-4 h-4 rounded accent-indigo-500 shrink-0"
                                        />
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium text-white truncate">{item.label}</p>
                                            <p className="text-xs text-zinc-500">{item.sublabel} · {format(new Date(item.date), "d MMM yyyy", { locale: es })}</p>
                                        </div>
                                        <span className={cn("text-sm font-semibold shrink-0", typeConfig[item.type].color)}>
                                            {fmt(item.amount)}
                                        </span>
                                    </label>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* Panel derecho: resumen + config */}
                <div className="space-y-5">
                    {/* Resumen selección */}
                    <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-5">
                        <h3 className="text-sm font-semibold text-white mb-4">Resumen remesa</h3>
                        {selected.length === 0 ? (
                            <p className="text-xs text-zinc-500 text-center py-4">Selecciona conceptos para incluir en la remesa.</p>
                        ) : (
                            <div className="space-y-2">
                                {(["cobros", "pagos", "nominas"] as RemesaType[]).map(t => {
                                    const tItems = selected.filter(i => i.type === t);
                                    if (!tItems.length) return null;
                                    return (
                                        <div key={t} className="flex items-center justify-between text-sm">
                                            <span className={cn("text-xs", typeConfig[t].color)}>{typeConfig[t].label} ({tItems.length})</span>
                                            <span className="text-zinc-300 font-medium">{fmt(tItems.reduce((s, i) => s + i.amount, 0))}</span>
                                        </div>
                                    );
                                })}
                                <div className="pt-3 mt-3 border-t border-[#27272a] flex items-center justify-between">
                                    <span className="text-sm font-semibold text-zinc-200">Total</span>
                                    <span className="text-base font-bold text-white">{fmt(totalSelected)}</span>
                                </div>
                                <div className="text-xs text-zinc-500 pt-1">{selected.length} concepto{selected.length !== 1 ? "s" : ""} incluido{selected.length !== 1 ? "s" : ""}</div>
                            </div>
                        )}
                    </div>

                    {/* Config SEPA */}
                    <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-5">
                        <h3 className="text-sm font-semibold text-white mb-4">Configuración SEPA</h3>
                        <div className="space-y-3 text-xs">
                            <div className="flex justify-between">
                                <span className="text-zinc-500">Identificador Acreedor</span>
                                <span className="font-mono text-zinc-300">ES99000B00000000</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-zinc-500">Banco por defecto</span>
                                <span className="text-zinc-300">BBVA Empresas</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-zinc-500">Esquema</span>
                                <span className="text-zinc-300">SEPA Credit Transfer (SCT)</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-zinc-500">Firma conjunta</span>
                                <span className="text-emerald-400 font-medium">Activada</span>
                            </div>
                        </div>
                    </div>

                    {/* Aviso automatización */}
                    <div className="rounded-2xl border border-blue-500/20 bg-blue-500/5 p-5">
                        <h3 className="text-xs font-semibold text-blue-400 mb-2">Automatización SEPA</h3>
                        <p className="text-xs text-zinc-400 leading-relaxed">
                            El sistema agrupa automáticamente los pagos validados en ficheros SEPA los días 5 y 20 de cada mes y los envía a tu gestoría.
                        </p>
                    </div>
                </div>
            </div>

            {/* Modal resultado agente */}
            {showModal && (
                <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={() => { if (agent.status !== "creating" && agent.status !== "polling") setShowModal(false); }}>
                    <div className="w-full max-w-md bg-[#111113] border border-[#27272a] rounded-2xl overflow-hidden" onClick={e => e.stopPropagation()}>
                        <div className="flex items-center justify-between px-6 py-4 border-b border-[#27272a]">
                            <h2 className="font-semibold text-white">Generando Remesa SEPA</h2>
                            {agent.status !== "creating" && agent.status !== "polling" && (
                                <button onClick={() => { setShowModal(false); agent.reset(); }} className="text-zinc-500 hover:text-white">
                                    <X className="w-5 h-5" />
                                </button>
                            )}
                        </div>
                        <div className="p-8 flex flex-col items-center text-center gap-4">
                            {(agent.status === "creating" || agent.status === "polling") && (
                                <>
                                    <Loader2 className="w-12 h-12 text-indigo-400 animate-spin" />
                                    <div>
                                        <p className="text-white font-semibold mb-1">El agente está procesando la remesa</p>
                                        <p className="text-xs text-zinc-500">Agrupando {selected.length} concepto{selected.length !== 1 ? "s" : ""} por {fmt(totalSelected)}…</p>
                                    </div>
                                </>
                            )}
                            {agent.status === "done" && (
                                <>
                                    <CheckCircle2 className="w-12 h-12 text-emerald-400" />
                                    <div>
                                        <p className="text-white font-semibold mb-1">Remesa generada correctamente</p>
                                        <p className="text-xs text-zinc-400 mb-4">El fichero SEPA XML ha sido creado y registrado en Documentos.</p>
                                    </div>
                                    <div className="flex gap-3 w-full">
                                        <button
                                            onClick={() => { setShowModal(false); agent.reset(); setItems(prev => prev.map(i => ({ ...i, selected: false }))); }}
                                            className="flex-1 py-2.5 bg-[#1c1c1e] hover:bg-zinc-800 border border-[#3f3f46] text-white rounded-xl text-sm font-medium transition-colors"
                                        >
                                            Cerrar
                                        </button>
                                        <button className="flex-1 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-sm font-medium transition-colors flex items-center justify-center gap-2">
                                            <Download className="w-4 h-4" /> Ver en Documentos
                                        </button>
                                    </div>
                                </>
                            )}
                            {agent.status === "failed" && (
                                <>
                                    <AlertCircle className="w-12 h-12 text-red-400" />
                                    <div>
                                        <p className="text-white font-semibold mb-1">Error al generar la remesa</p>
                                        <p className="text-xs text-red-400 mb-4">{agent.error || "Error desconocido"}</p>
                                    </div>
                                    <button onClick={() => { setShowModal(false); agent.reset(); }} className="w-full py-2.5 bg-[#1c1c1e] hover:bg-zinc-800 border border-[#3f3f46] text-white rounded-xl text-sm font-medium transition-colors">
                                        Cerrar
                                    </button>
                                </>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Toast */}
            {toast && (
                <div className={cn("fixed bottom-6 right-6 z-50 flex items-center gap-3 px-5 py-3 rounded-2xl shadow-2xl text-sm font-medium",
                    toast.type === "ok" ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400" : "bg-red-500/10 border border-red-500/20 text-red-400")}>
                    {toast.type === "ok" ? <CheckCircle2 className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
                    {toast.msg}
                    <button onClick={() => setToast(null)}><X className="w-4 h-4 opacity-60 hover:opacity-100" /></button>
                </div>
            )}
        </div>
    );
}
