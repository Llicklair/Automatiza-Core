"use client";

import { useEffect, useState } from "react";
import { api, Invoice, Client } from "@/lib/api";
import {
    ArrowDownToLine, FileText, CheckCircle2, Clock, Search, Plus, X, Loader2, Inbox, Trash2
} from "lucide-react";
import { useToastStore } from "@/stores/toast";

function StatusBadge({ status }: { status: string }) {
    switch (status) {
        case "draft":     return <span className="text-[10px] uppercase font-bold text-zinc-500 bg-zinc-500/10 px-2.5 py-1 rounded-full border border-zinc-500/20">Borrador</span>;
        case "pending":   return <span className="text-[10px] uppercase font-bold text-amber-500 bg-amber-500/10 px-2.5 py-1 rounded-full border border-amber-500/20">Pendiente</span>;
        case "paid":      return <span className="text-[10px] uppercase font-bold text-emerald-500 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">Pagada</span>;
        case "cancelled": return <span className="text-[10px] uppercase font-bold text-red-500 bg-red-500/10 px-2.5 py-1 rounded-full border border-red-500/20">Cancelada</span>;
        default:          return <span className="text-[10px] uppercase font-bold text-zinc-500 bg-zinc-500/10 px-2.5 py-1 rounded-full border border-zinc-500/20">{status}</span>;
    }
}

const today = () => new Date().toISOString().slice(0, 10);

export default function FacturasRecibidasPage() {
    const toast = useToastStore();
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [clients, setClients] = useState<Client[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState("");

    // Modal registro manual
    const [showModal, setShowModal] = useState(false);
    const [supplierId, setSupplierId] = useState("");
    const [supplierName, setSupplierName] = useState("");
    const [useExisting, setUseExisting] = useState(true);
    const [invoiceNumber, setInvoiceNumber] = useState("");
    const [amount, setAmount] = useState("");
    const [taxPct, setTaxPct] = useState("21");
    const [date, setDate] = useState(today());
    const [dueDate, setDueDate] = useState("");
    const [invStatus, setInvStatus] = useState("pending");
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => { loadData(); }, []);

    const loadData = async () => {
        setLoading(true);
        try {
            const [allInvoices, allClients] = await Promise.all([
                api.erp.invoices.list({ limit: 200 }),
                api.erp.clients.list({ limit: 200 }),
            ]);
            setInvoices(allInvoices.filter(i => i.invoice_type === "received"));
            setClients(allClients);
        } catch { /* silent */ }
        finally { setLoading(false); }
    };

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            let clientId = supplierId;
            // Crear proveedor nuevo si no se eligió uno existente
            if (!useExisting || !supplierId) {
                if (!supplierName.trim()) { toast.warning("Indica el nombre del proveedor"); setSubmitting(false); return; }
                const newClient = await api.erp.clients.create({ name: supplierName, client_type: "supplier" });
                clientId = newClient.id;
            }
            const baseAmount = parseFloat(amount) || 0;
            const tax = baseAmount * (parseFloat(taxPct) / 100);
            const inv = await api.erp.invoices.create(clientId, {
                invoice_number: invoiceNumber || null,
                date: new Date(date).toISOString(),
                due_date: dueDate ? new Date(dueDate).toISOString() : null,
                status: invStatus,
                invoice_type: "received",
                lines: [{
                    description: "Factura recibida",
                    quantity: 1,
                    unit_price: baseAmount,
                    discount_percentage: 0,
                    tax_percentage: parseFloat(taxPct),
                }],
            } as any);
            setInvoices(prev => [inv, ...prev]);
            setShowModal(false);
            resetModal();
        } catch (err: any) {
            toast.error(err?.message || "Error registrando factura");
        } finally {
            setSubmitting(false);
        }
    };

    const resetModal = () => {
        setSupplierId(""); setSupplierName(""); setUseExisting(true);
        setInvoiceNumber(""); setAmount(""); setTaxPct("21");
        setDate(today()); setDueDate(""); setInvStatus("pending");
    };

    const handleStatusChange = async (invId: string, nextStatus: string) => {
        try {
            const updated = await api.erp.invoices.updateStatus(invId, nextStatus);
            setInvoices(prev => prev.map(i => i.id === invId ? updated : i));
        } catch (err: any) {
            toast.error(err?.message || "Error cambiando estado");
        }
    };

    const handleDeleteInvoice = async (id: string) => {
        if (!confirm("¿Eliminar esta factura? Esta acción no se puede deshacer.")) return;
        try {
            await api.erp.invoices.delete(id);
            setInvoices(prev => prev.filter(i => i.id !== id));
            toast.success("Factura eliminada");
        } catch (err: any) {
            toast.error(err?.message || "Error al eliminar factura");
        }
    };

    const filtered = invoices.filter(i =>
        (i.invoice_number || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
        (i.client?.name || "").toLowerCase().includes(searchTerm.toLowerCase())
    );

    const totalPendiente = invoices.filter(i => i.status === "pending").reduce((a, b) => a + Number(b.amount_total), 0);
    const thirtyDaysAgo = new Date(); thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    const totalPagado30 = invoices
        .filter(i => i.status === "paid" && new Date(i.created_at) >= thirtyDaysAgo)
        .reduce((a, b) => a + Number(b.amount_total), 0);

    return (
        <div className="p-8 max-w-6xl mx-auto space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white tracking-tight">Facturas Recibidas</h1>
                    <p className="mt-1 text-sm text-zinc-400">Gestiona tus compras, gastos y proveedores.</p>
                </div>
                <button
                    onClick={() => setShowModal(true)}
                    className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl font-medium transition-colors text-sm shadow-lg shadow-indigo-500/20"
                >
                    <Plus className="w-4 h-4" />
                    Registrar Factura
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-[#111113] border border-[#27272a] p-6 rounded-2xl flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
                        <Clock className="w-6 h-6 text-amber-500" />
                    </div>
                    <div>
                        <p className="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-1">Pendiente de Pago</p>
                        <p className="text-2xl font-bold text-amber-500">{totalPendiente.toLocaleString("es-ES", { minimumFractionDigits: 2 })}€</p>
                    </div>
                </div>
                <div className="bg-[#111113] border border-[#27272a] p-6 rounded-2xl flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                        <CheckCircle2 className="w-6 h-6 text-emerald-500" />
                    </div>
                    <div>
                        <p className="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-1">Pagado (últimos 30d)</p>
                        <p className="text-2xl font-bold text-emerald-500">{totalPagado30.toLocaleString("es-ES", { minimumFractionDigits: 2 })}€</p>
                    </div>
                </div>
            </div>

            <div className="bg-[#111113] border border-[#27272a] rounded-2xl overflow-hidden shadow-xl shadow-black/20">
                <div className="p-5 border-b border-[#27272a]">
                    <div className="relative max-w-md">
                        <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                            type="text"
                            placeholder="Buscar por proveedor o número..."
                            value={searchTerm}
                            onChange={e => setSearchTerm(e.target.value)}
                            className="w-full bg-[#18181b] border border-[#3f3f46] rounded-xl pl-9 pr-4 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition-colors"
                        />
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="border-b border-[#27272a] bg-black/20 text-xs font-semibold text-zinc-500 uppercase tracking-wider">
                                <th className="py-4 pl-6 font-medium">Proveedor</th>
                                <th className="py-4 font-medium">Estado</th>
                                <th className="py-4 font-medium text-right">Fecha</th>
                                <th className="py-4 font-medium text-right">Vencimiento</th>
                                <th className="py-4 font-medium text-right pr-6">Monto</th>
                                <th className="py-4 font-medium pr-6">Acción</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-[#27272a]">
                            {loading ? (
                                <tr><td colSpan={6} className="py-12 text-center text-zinc-500 text-sm">Cargando facturas...</td></tr>
                            ) : filtered.length === 0 ? (
                                <tr><td colSpan={6} className="py-16 text-center">
                                    <Inbox className="w-10 h-10 text-zinc-700 mx-auto mb-3" />
                                    <p className="text-zinc-500 text-sm">{invoices.length === 0 ? "No tienes facturas de compra registradas" : "Sin resultados"}</p>
                                    {invoices.length === 0 && (
                                        <button onClick={() => setShowModal(true)} className="mt-4 text-indigo-400 hover:text-indigo-300 text-sm underline">
                                            Registrar primera factura
                                        </button>
                                    )}
                                </td></tr>
                            ) : filtered.map(inv => (
                                <tr key={inv.id} className="hover:bg-white/[0.02] transition-colors">
                                    <td className="py-4 pl-6">
                                        <div className="font-semibold text-white">{inv.client?.name || "Desconocido"}</div>
                                        <div className="text-xs text-zinc-500 font-mono mt-0.5">{inv.invoice_number || "S/N"}</div>
                                    </td>
                                    <td className="py-4"><StatusBadge status={inv.status} /></td>
                                    <td className="py-4 text-right text-sm text-zinc-400">{inv.date ? new Date(inv.date).toLocaleDateString("es-ES") : "—"}</td>
                                    <td className="py-4 text-right text-sm text-zinc-400">{inv.due_date ? new Date(inv.due_date).toLocaleDateString("es-ES") : "—"}</td>
                                    <td className="py-4 pr-6 text-right font-bold text-white">{Number(inv.amount_total).toLocaleString("es-ES", { minimumFractionDigits: 2 })}€</td>
                                    <td className="py-4 pr-6">
                                        <div className="flex items-center justify-end gap-2">
                                            {inv.status === "pending" && (
                                                <button
                                                    onClick={() => handleStatusChange(inv.id, "paid")}
                                                    className="text-xs text-emerald-400 hover:text-emerald-300 border border-emerald-500/20 hover:border-emerald-400/40 rounded-lg px-2.5 py-1.5 transition-all"
                                                >
                                                    Marcar pagada
                                                </button>
                                            )}
                                            <button
                                                onClick={() => handleDeleteInvoice(inv.id)}
                                                title="Eliminar factura"
                                                className="inline-flex items-center text-xs text-red-400/60 hover:text-red-400 hover:bg-red-500/10 rounded-lg p-1.5 transition-all"
                                            >
                                                <Trash2 className="w-3.5 h-3.5" />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Modal registrar factura recibida */}
            {showModal && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-[#111113] border border-zinc-800 rounded-2xl w-full max-w-lg shadow-2xl">
                        <div className="p-5 border-b border-zinc-800 flex justify-between items-center bg-[#161618]">
                            <h2 className="text-lg font-medium text-white flex items-center gap-2">
                                <ArrowDownToLine className="w-4 h-4 text-indigo-400" />
                                Registrar Factura Recibida
                            </h2>
                            <button onClick={() => { setShowModal(false); resetModal(); }} className="text-zinc-400 hover:text-white">
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <form onSubmit={handleRegister} className="p-6 space-y-4">
                            <div>
                                <label className="block text-sm text-zinc-400 mb-1.5">Proveedor *</label>
                                <div className="flex gap-2 mb-2">
                                    <button type="button" onClick={() => setUseExisting(true)} className={`text-xs px-3 py-1 rounded-lg border transition-colors ${useExisting ? "bg-indigo-600 border-indigo-500 text-white" : "border-zinc-700 text-zinc-400 hover:text-white"}`}>Existente</button>
                                    <button type="button" onClick={() => setUseExisting(false)} className={`text-xs px-3 py-1 rounded-lg border transition-colors ${!useExisting ? "bg-indigo-600 border-indigo-500 text-white" : "border-zinc-700 text-zinc-400 hover:text-white"}`}>Nuevo</button>
                                </div>
                                {useExisting ? (
                                    <select
                                        value={supplierId}
                                        onChange={e => setSupplierId(e.target.value)}
                                        required={useExisting}
                                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                                    >
                                        <option value="">Seleccionar proveedor…</option>
                                        {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                                    </select>
                                ) : (
                                    <input
                                        type="text"
                                        required={!useExisting}
                                        value={supplierName}
                                        onChange={e => setSupplierName(e.target.value)}
                                        placeholder="Nombre del proveedor"
                                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                                    />
                                )}
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm text-zinc-400 mb-1.5">Nº Factura</label>
                                    <input
                                        type="text"
                                        value={invoiceNumber}
                                        onChange={e => setInvoiceNumber(e.target.value)}
                                        placeholder="Opcional"
                                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm text-zinc-400 mb-1.5">Estado</label>
                                    <select
                                        value={invStatus}
                                        onChange={e => setInvStatus(e.target.value)}
                                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                                    >
                                        <option value="pending">Pendiente</option>
                                        <option value="paid">Pagada</option>
                                        <option value="draft">Borrador</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm text-zinc-400 mb-1.5">Importe base (€) *</label>
                                    <input
                                        type="number"
                                        required
                                        min="0"
                                        step="0.01"
                                        value={amount}
                                        onChange={e => setAmount(e.target.value)}
                                        placeholder="0.00"
                                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm text-zinc-400 mb-1.5">% IVA</label>
                                    <select
                                        value={taxPct}
                                        onChange={e => setTaxPct(e.target.value)}
                                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                                    >
                                        <option value="21">21%</option>
                                        <option value="10">10%</option>
                                        <option value="4">4%</option>
                                        <option value="0">0%</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm text-zinc-400 mb-1.5">Fecha *</label>
                                    <input
                                        type="date"
                                        required
                                        value={date}
                                        onChange={e => setDate(e.target.value)}
                                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm text-zinc-400 mb-1.5">Vencimiento</label>
                                    <input
                                        type="date"
                                        value={dueDate}
                                        onChange={e => setDueDate(e.target.value)}
                                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                                    />
                                </div>
                            </div>

                            <div className="pt-2 flex justify-end gap-3">
                                <button
                                    type="button"
                                    onClick={() => { setShowModal(false); resetModal(); }}
                                    className="px-4 py-2 text-zinc-300 hover:text-white border border-zinc-700 rounded-lg text-sm"
                                >
                                    Cancelar
                                </button>
                                <button
                                    type="submit"
                                    disabled={submitting}
                                    className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
                                >
                                    {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                                    Registrar
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
