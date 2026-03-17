"use client";

import { useEffect, useState } from "react";
import { api, Quote, Client, Product } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";
import {
    FileText, Plus, Search, FileSignature, CheckCircle2,
    XCircle, Clock, Send, FilePlus2, DollarSign,
    FileCheck2, Loader2, AlertCircle, X, Trash2
} from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";

export default function QuotesPage() {
    const toastNotif = useToastStore();
    const [quotes, setQuotes] = useState<Quote[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);

    // Formularios
    const [clients, setClients] = useState<Client[]>([]);
    const [products, setProducts] = useState<Product[]>([]);

    // Nuevo Presupuesto State
    const [selectedClient, setSelectedClient] = useState("");
    const [validUntil, setValidUntil] = useState("");
    const [lines, setLines] = useState([{ product_id: "", description: "", quantity: 1, unit_price: 0, tax_percentage: 21 }]);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [convertingId, setConvertingId] = useState<string | null>(null);
    const [toast, setToast] = useState<{ msg: string; type: "ok" | "err" } | null>(null);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        setIsLoading(true);
        try {
            const [quotesRes, clientsRes, prodRes] = await Promise.all([
                api.erp.quotes.list(),
                api.erp.clients.list(),
                api.erp.products.list()
            ]);
            setQuotes(quotesRes);
            setClients(clientsRes);
            setProducts(prodRes);
        } catch (error) {
            logError("ventas/presupuestos/page", error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSubmitting(true);
        try {
            await api.erp.quotes.create({
                client_id: selectedClient,
                date: new Date().toISOString(),
                valid_until: validUntil ? new Date(validUntil).toISOString() : null,
                status: "draft",
                lines: lines.map(l => ({
                    ...l,
                    product_id: l.product_id || null
                })) as any
            });
            setShowModal(false);
            resetForm();
            await loadData();
        } catch (error) {
            logError("ventas/presupuestos/page", error);
            toastNotif.error("Error al emitir presupuesto");
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleConvert = async (q: Quote) => {
        if (!await showConfirm({ message: `¿Convertir el presupuesto a factura? Se creará una factura de ${formatCurrency(q.amount_total)} para ${q.client?.name ?? 'este cliente'}.`, confirmLabel: "Confirmar", confirmVariant: "primary" })) return;
        setConvertingId(q.id);
        try {
            const result = await api.erp.quotes.convertToInvoice(q.id);
            setToast({ msg: `✓ Factura ${result.invoice_number} creada correctamente (${formatCurrency(result.amount_total)})`, type: "ok" });
            await loadData();
        } catch (e: any) {
            setToast({ msg: "Error: " + (e.message || "No se pudo convertir"), type: "err" });
        } finally {
            setConvertingId(null);
            setTimeout(() => setToast(null), 6000);
        }
    };

    const handleDelete = async (id: string) => {
        if (!await showConfirm({ message: "¿Eliminar este presupuesto?", confirmLabel: "Eliminar", confirmVariant: "danger" })) return;
        try {
            await api.erp.quotes.delete(id);
            setQuotes(prev => prev.filter(q => q.id !== id));
        } catch (e: any) {
            setToast({ msg: "Error al eliminar: " + (e.message || ""), type: "err" });
            setTimeout(() => setToast(null), 4000);
        }
    };

    const handleStatusChange = async (id: string, newStatus: string) => {
        try {
            // Optimistic update
            setQuotes(prev => prev.map(q => q.id === id ? { ...q, status: newStatus } : q));
            await api.erp.quotes.update(id, { status: newStatus });
        } catch (error) {
            logError("ventas/presupuestos/page", error);
            await loadData(); // Revert
        }
    };

    const resetForm = () => {
        setSelectedClient("");
        setValidUntil("");
        setLines([{ product_id: "", description: "", quantity: 1, unit_price: 0, tax_percentage: 21 }]);
    };

    const updateLine = (index: number, field: string, value: any) => {
        const newLines = [...lines];
        if (field === "product_id" && value) {
            const prod = products.find(p => p.id === value);
            if (prod) {
                newLines[index].description = prod.name;
                newLines[index].unit_price = prod.price;
                newLines[index].tax_percentage = prod.tax_percentage;
            }
        }
        (newLines[index] as any)[field] = value;
        setLines(newLines);
    };

    const formatCurrency = (val: number) => {
        return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(val);
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'draft':
                return <span className="flex items-center gap-1.5 px-3 py-1 bg-zinc-800 text-zinc-300 border border-zinc-700 rounded-full text-xs font-medium"><FileSignature className="w-3.5 h-3.5" /> Borrador</span>;
            case 'sent':
                return <span className="flex items-center gap-1.5 px-3 py-1 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-full text-xs font-medium"><Send className="w-3.5 h-3.5" /> Enviado</span>;
            case 'accepted':
                return <span className="flex items-center gap-1.5 px-3 py-1 bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 rounded-full text-xs font-medium"><CheckCircle2 className="w-3.5 h-3.5" /> Aceptado</span>;
            case 'rejected':
                return <span className="flex items-center gap-1.5 px-3 py-1 bg-red-500/10 text-red-500 border border-red-500/20 rounded-full text-xs font-medium"><XCircle className="w-3.5 h-3.5" /> Rechazado</span>;
            default:
                return null;
        }
    };

    return (
        <div className="min-h-screen bg-[#09090b] text-white p-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
                <div>
                    <h1 className="text-3xl font-light text-white flex items-center gap-3">
                        <div className="p-2 bg-indigo-500/10 rounded-xl">
                            <FileText className="w-8 h-8 text-indigo-400" />
                        </div>
                        Presupuestos
                    </h1>
                    <p className="text-zinc-400 mt-2 ml-14 text-sm max-w-2xl">
                        Crea propuestas comerciales manualmente o revisa las pre-generadas por la Inteligencia Artificial a partir del CRM.
                    </p>
                </div>

                <div className="flex gap-3">
                    <button
                        onClick={() => setShowModal(true)}
                        className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/20 px-5 py-2.5 rounded-full font-medium transition-colors"
                    >
                        <Plus className="w-4 h-4" />
                        Crear Presupuesto
                    </button>
                    <button className="flex items-center gap-2 bg-[#111113] border border-zinc-800 hover:bg-zinc-800 text-white px-5 py-2.5 rounded-full font-medium transition-colors">
                        <Clock className="w-4 h-4 text-zinc-400" />
                        Expirados
                    </button>
                </div>
            </div>

            <div className="bg-[#111113] border border-zinc-800 rounded-2xl overflow-hidden shadow-xl">
                <div className="p-4 border-b border-zinc-800 flex justify-between items-center bg-[#161618]">
                    <div className="relative">
                        <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                            type="text"
                            placeholder="Buscar cliente o nº..."
                            className="bg-[#09090b] border border-zinc-800 text-sm text-white rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:border-indigo-500 transition-colors w-72"
                        />
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm whitespace-nowrap">
                        <thead className="bg-[#161618]/50 text-zinc-400 border-b border-zinc-800">
                            <tr>
                                <th className="px-6 py-4 font-medium">Nº Propuesta</th>
                                <th className="px-6 py-4 font-medium">Cliente</th>
                                <th className="px-6 py-4 font-medium">Fecha</th>
                                <th className="px-6 py-4 font-medium text-right">Base</th>
                                <th className="px-6 py-4 font-medium text-right text-indigo-400">Total</th>
                                <th className="px-6 py-4 font-medium">Estado</th>
                                <th className="px-6 py-4 font-medium text-right">Acción</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-800/50">
                            {isLoading ? (
                                <tr>
                                    <td colSpan={7} className="px-6 py-12 text-center">
                                        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-500 mx-auto"></div>
                                    </td>
                                </tr>
                            ) : quotes.length === 0 ? (
                                <tr>
                                    <td colSpan={7} className="px-6 py-16 text-center">
                                        <FilePlus2 className="w-10 h-10 text-zinc-600 mx-auto mb-3" />
                                        <p className="text-zinc-400 font-medium">Agrega tu primer presupuesto para empezar</p>
                                    </td>
                                </tr>
                            ) : quotes.map((q) => (
                                <tr key={q.id} className="hover:bg-indigo-500/[0.02] transition-colors group">
                                    <td className="px-6 py-4 font-medium text-white">
                                        {q.quote_number || 'Borrador'}
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-3">
                                            <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center text-zinc-400 font-medium">
                                                {q.client?.name.charAt(0) || '?'}
                                            </div>
                                            <span className="font-medium text-zinc-300">{q.client?.name || 'Cliente sin nombre'}</span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-zinc-400">
                                        {format(new Date(q.date), "dd/MM/yyyy")}
                                    </td>
                                    <td className="px-6 py-4 text-right text-zinc-300">
                                        {formatCurrency(q.amount_base)}
                                    </td>
                                    <td className="px-6 py-4 text-right font-semibold text-indigo-400">
                                        {formatCurrency(q.amount_total)}
                                    </td>
                                    <td className="px-6 py-4">
                                        {getStatusBadge(q.status)}
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <div className="flex items-center justify-end gap-2">
                                            {/* Convertir en Factura */}
                                            {q.status !== "rejected" && q.status !== "accepted" && (
                                                <button
                                                    onClick={() => handleConvert(q)}
                                                    disabled={convertingId === q.id}
                                                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-emerald-400 hover:text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 rounded-lg transition-colors disabled:opacity-50"
                                                    title="Convertir en Factura"
                                                >
                                                    {convertingId === q.id
                                                        ? <Loader2 className="w-3 h-3 animate-spin" />
                                                        : <FileCheck2 className="w-3 h-3" />}
                                                    Facturar
                                                </button>
                                            )}
                                            {q.status === "accepted" && (
                                                <span className="text-xs text-zinc-500 italic">Factura emitida</span>
                                            )}
                                            {/* Cambiar estado */}
                                            <select
                                                value={q.status}
                                                onChange={(e) => handleStatusChange(q.id, e.target.value)}
                                                className="bg-[#09090b] text-xs border border-zinc-700 rounded pl-2 pr-6 py-1.5 text-zinc-400 hover:text-white transition-colors cursor-pointer"
                                            >
                                                <option value="draft">Borrador</option>
                                                <option value="sent">Enviado</option>
                                                <option value="accepted">Aceptado</option>
                                                <option value="rejected">Rechazado</option>
                                            </select>
                                            {/* Eliminar */}
                                            <button
                                                onClick={() => handleDelete(q.id)}
                                                className="p-1.5 rounded-lg text-zinc-600 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                                                title="Eliminar presupuesto"
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

            {/* Modal Crear Presupuesto Rápido */}
            {showModal && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-[#111113] border border-zinc-800 rounded-2xl w-full max-w-3xl overflow-hidden shadow-2xl">
                        <div className="p-5 border-b border-zinc-800 flex justify-between items-center bg-[#161618]">
                            <h2 className="text-lg font-medium text-white flex items-center gap-2">
                                <FileText className="w-4 h-4 text-indigo-400" />
                                Nuevo Presupuesto
                            </h2>
                            <button onClick={() => setShowModal(false)} className="text-zinc-400 hover:text-white">✕</button>
                        </div>

                        <form onSubmit={handleCreate} className="p-6 space-y-6">
                            <div className="grid grid-cols-2 gap-6 border-b border-zinc-800/50 pb-6">
                                <div>
                                    <label className="block text-sm text-zinc-400 mb-1.5">Cliente</label>
                                    <select
                                        required
                                        value={selectedClient}
                                        onChange={e => setSelectedClient(e.target.value)}
                                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-indigo-500"
                                    >
                                        <option value="" disabled>Selecciona o busca...</option>
                                        {clients.map(c => (
                                            <option key={c.id} value={c.id}>{c.name}</option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm text-zinc-400 mb-1.5">Válido hasta</label>
                                    <input
                                        type="date"
                                        value={validUntil}
                                        onChange={e => setValidUntil(e.target.value)}
                                        className="w-full bg-[#09090b] border border-zinc-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-indigo-500"
                                    />
                                </div>
                            </div>

                            <div>
                                <div className="flex justify-between items-center mb-3">
                                    <label className="block text-sm font-medium text-zinc-300">Líneas (Conceptos)</label>
                                    <button
                                        type="button"
                                        onClick={() => setLines([...lines, { product_id: "", description: "", quantity: 1, unit_price: 0, tax_percentage: 21 }])}
                                        className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium"
                                    >
                                        <Plus className="w-3 h-3" /> Añadir concepto
                                    </button>
                                </div>
                                <div className="space-y-3">
                                    {lines.map((l, i) => (
                                        <div key={i} className="flex gap-3 items-start bg-[#161618] p-3 rounded-lg border border-zinc-800/50">
                                            <div className="flex-1">
                                                <input
                                                    type="text"
                                                    required
                                                    value={l.description}
                                                    onChange={e => updateLine(i, 'description', e.target.value)}
                                                    placeholder="Descripción del concepto"
                                                    className="w-full bg-[#09090b] border border-zinc-800 rounded px-3 py-1.5 text-sm text-white focus:border-indigo-500"
                                                />
                                                <div className="mt-2 text-xs flex gap-2">
                                                    <select
                                                        value={l.product_id}
                                                        onChange={e => updateLine(i, 'product_id', e.target.value)}
                                                        className="bg-[#09090b] border border-zinc-800 rounded px-2 text-zinc-400"
                                                    >
                                                        <option value="">Rellenado libre</option>
                                                        {products.map(p => <option key={p.id} value={p.id}>Catálogo: {p.name}</option>)}
                                                    </select>
                                                </div>
                                            </div>
                                            <div className="w-20">
                                                <input
                                                    type="number"
                                                    min="1"
                                                    value={l.quantity}
                                                    onChange={e => updateLine(i, 'quantity', parseFloat(e.target.value))}
                                                    className="w-full bg-[#09090b] border border-zinc-800 rounded px-3 py-1.5 text-sm text-center text-white focus:border-indigo-500"
                                                />
                                                <span className="text-[10px] text-zinc-500 block text-center mt-1">Uds.</span>
                                            </div>
                                            <div className="w-28 relative">
                                                <DollarSign className="w-3 h-3 text-zinc-500 absolute left-2 top-2.5" />
                                                <input
                                                    type="number"
                                                    step="0.01"
                                                    value={l.unit_price}
                                                    onChange={e => updateLine(i, 'unit_price', parseFloat(e.target.value))}
                                                    className="w-full bg-[#09090b] border border-zinc-800 rounded pl-6 pr-2 py-1.5 text-sm text-right text-white focus:border-indigo-500"
                                                />
                                                <span className="text-[10px] text-zinc-500 block text-right mt-1 pr-1">Precio Un.</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="pt-4 flex justify-end gap-3 mt-4">
                                <button
                                    type="button"
                                    onClick={() => setShowModal(false)}
                                    className="px-5 py-2.5 text-zinc-300 hover:text-white transition-colors font-medium border border-transparent hover:border-zinc-700 rounded-lg"
                                >
                                    Cancelar
                                </button>
                                <button
                                    type="submit"
                                    disabled={isSubmitting || !selectedClient || lines.some(l => !l.description)}
                                    className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2.5 rounded-lg font-medium transition-colors shadow-lg shadow-indigo-500/20 disabled:opacity-50"
                                >
                                    {isSubmitting ? "Guardando..." : "Crear Borrador"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Toast */}
            {toast && (
                <div className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-5 py-3 rounded-2xl shadow-2xl text-sm font-medium max-w-sm ${toast.type === "ok"
                    ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400"
                    : "bg-red-500/10 border border-red-500/20 text-red-400"
                    }`}>
                    {toast.type === "ok" ? <CheckCircle2 className="w-5 h-5 flex-shrink-0" /> : <AlertCircle className="w-5 h-5 flex-shrink-0" />}
                    <span className="flex-1">{toast.msg}</span>
                    <button onClick={() => setToast(null)} className="opacity-60 hover:opacity-100"><X className="w-4 h-4" /></button>
                </div>
            )}
        </div>
    );
}
