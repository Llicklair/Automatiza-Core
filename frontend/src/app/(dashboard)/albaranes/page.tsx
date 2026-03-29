"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { DeliveryNote, DeliveryNoteCreate } from "@/lib/api/albaranes";
import {
    Plus, Loader2, FileText, Trash2, Download, CheckCircle2,
    Truck, FileEdit, Search, X, ChevronDown,
} from "lucide-react";
import { useToastStore } from "@/stores/toast";
import { logError } from "@/lib/logger";

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
    draft:     { label: "Borrador",   color: "text-zinc-400 bg-zinc-400/10 border-zinc-400/20" },
    confirmed: { label: "Confirmado", color: "text-indigo-400 bg-indigo-400/10 border-indigo-400/20" },
    delivered: { label: "Entregado",  color: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20" },
};

const fmt = (n: number) => n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });

type LineForm = { description: string; quantity: string; unit_price: string; tax_percentage: string };

const emptyLine = (): LineForm => ({ description: "", quantity: "1", unit_price: "0", tax_percentage: "21" });

export default function AlbaranesPage() {
    const toast = useToastStore();
    const router = useRouter();
    const [albaranes, setAlbaranes] = useState<DeliveryNote[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [filterStatus, setFilterStatus] = useState("");

    // Modal
    const [showModal, setShowModal] = useState(false);
    const [saving, setSaving] = useState(false);
    const [clientName, setClientName] = useState("");
    const [date, setDate] = useState(new Date().toISOString().split("T")[0]);
    const [notes, setNotes] = useState("");
    const [lines, setLines] = useState<LineForm[]>([emptyLine(), emptyLine()]);

    const loadData = async () => {
        setLoading(true);
        try { setAlbaranes(await api.albaranes.list()); }
        catch (e) { logError("albaranes/page", e); }
        finally { setLoading(false); }
    };

    useEffect(() => { loadData(); }, []);

    const resetModal = () => {
        setClientName(""); setDate(new Date().toISOString().split("T")[0]);
        setNotes(""); setLines([emptyLine(), emptyLine()]);
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        const validLines = lines.filter(l => l.description.trim());
        if (!validLines.length) { toast.warning("Añade al menos una línea con descripción."); return; }
        setSaving(true);
        try {
            const payload: DeliveryNoteCreate = {
                client_name: clientName || undefined,
                date,
                notes: notes || undefined,
                lines: validLines.map(l => ({
                    description: l.description,
                    quantity: parseFloat(l.quantity) || 1,
                    unit_price: parseFloat(l.unit_price) || 0,
                    tax_percentage: parseFloat(l.tax_percentage) || 21,
                })),
            };
            await api.albaranes.create(payload);
            setShowModal(false); resetModal(); await loadData();
            toast.success("Albarán creado correctamente");
        } catch (e: any) { toast.error("Error creando albarán: " + e.message); }
        finally { setSaving(false); }
    };

    const handleDelete = async (id: string) => {
        if (!confirm("¿Eliminar este albarán?")) return;
        try { await api.albaranes.delete(id); setAlbaranes(prev => prev.filter(a => a.id !== id)); toast.success("Albarán eliminado"); }
        catch (e: any) { toast.error(e.message); }
    };

    const handleStatusChange = async (id: string, status: string) => {
        try {
            const updated = await api.albaranes.updateStatus(id, status);
            setAlbaranes(prev => prev.map(a => a.id === id ? updated : a));
        } catch (e: any) { toast.error(e.message); }
    };

    const handleDownloadPdf = (id: string) => {
        const token = localStorage.getItem("access_token");
        const base = process.env.NEXT_PUBLIC_API_URL || "";
        const url = `${base}${api.albaranes.pdfUrl(id)}`;
        const a = document.createElement("a");
        a.href = url;
        a.target = "_blank";
        if (token) a.href = url + `?token=${token}`;
        a.click();
    };

    const handleConvertToInvoice = (albaran: DeliveryNote) => {
        router.push(`/ventas/facturas/nueva?from_albaran=${albaran.id}`);
    };

    const filtered = albaranes.filter(a => {
        const matchSearch = !search || a.albaran_number.toLowerCase().includes(search.toLowerCase());
        const matchStatus = !filterStatus || a.status === filterStatus;
        return matchSearch && matchStatus;
    });

    return (
        <div className="p-8 max-w-[1400px] mx-auto space-y-6 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-1">Albaranes</h1>
                    <p className="text-zinc-400 text-sm">Gestión de albaranes y notas de entrega.</p>
                </div>
                <button
                    onClick={() => setShowModal(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors font-medium shadow-lg shadow-indigo-500/20"
                >
                    <Plus className="w-4 h-4" /> Nuevo Albarán
                </button>
            </div>

            {/* Filters */}
            <div className="flex gap-3 flex-wrap">
                <div className="relative flex-1 min-w-[200px]">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                    <input
                        value={search} onChange={e => setSearch(e.target.value)}
                        placeholder="Buscar por número..."
                        className="w-full pl-9 pr-3 py-2 rounded-lg bg-[#111113] border border-[#27272a] text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-indigo-500/50"
                    />
                </div>
                <select
                    value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
                    className="px-3 py-2 rounded-lg bg-[#111113] border border-[#27272a] text-sm text-white focus:outline-none focus:border-indigo-500/50"
                >
                    <option value="">Todos los estados</option>
                    <option value="draft">Borrador</option>
                    <option value="confirmed">Confirmado</option>
                    <option value="delivered">Entregado</option>
                </select>
            </div>

            {/* Table */}
            <div className="bg-[#111113] border border-[#27272a] rounded-2xl overflow-hidden shadow-2xl">
                {loading ? (
                    <div className="p-12 flex items-center justify-center gap-3 text-zinc-500">
                        <Loader2 className="w-5 h-5 animate-spin" /> Cargando albaranes...
                    </div>
                ) : filtered.length === 0 ? (
                    <div className="p-16 text-center">
                        <FileText className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-white mb-1">Sin albaranes</h3>
                        <p className="text-zinc-500 text-sm">Crea el primero con el botón &ldquo;Nuevo Albarán&rdquo;.</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm text-left">
                            <thead className="bg-[#18181b] text-zinc-400 border-b border-[#27272a]">
                                <tr>
                                    <th className="px-6 py-4 font-medium">Nº Albarán</th>
                                    <th className="px-6 py-4 font-medium">Fecha</th>
                                    <th className="px-6 py-4 font-medium">Cliente</th>
                                    <th className="px-6 py-4 font-medium">Estado</th>
                                    <th className="px-6 py-4 font-medium text-right">Total</th>
                                    <th className="px-6 py-4 font-medium w-48">Acciones</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-[#27272a]/50">
                                {filtered.map(albaran => {
                                    const st = STATUS_LABELS[albaran.status] || STATUS_LABELS.draft;
                                    return (
                                        <tr key={albaran.id} className="group hover:bg-white/[0.02] transition-colors">
                                            <td className="px-6 py-4 font-mono text-indigo-400 font-medium">{albaran.albaran_number}</td>
                                            <td className="px-6 py-4 text-zinc-300">{new Date(albaran.date).toLocaleDateString("es-ES")}</td>
                                            <td className="px-6 py-4 text-zinc-300">{albaran.client_id ? "—" : "Sin cliente"}</td>
                                            <td className="px-6 py-4">
                                                <select
                                                    value={albaran.status}
                                                    onChange={e => handleStatusChange(albaran.id, e.target.value)}
                                                    className={`text-xs px-2 py-1 rounded-full border font-medium bg-transparent cursor-pointer focus:outline-none ${st.color}`}
                                                >
                                                    <option value="draft">Borrador</option>
                                                    <option value="confirmed">Confirmado</option>
                                                    <option value="delivered">Entregado</option>
                                                </select>
                                            </td>
                                            <td className="px-6 py-4 text-right font-medium text-white">{fmt(albaran.amount_total)}</td>
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <button
                                                        onClick={() => handleDownloadPdf(albaran.id)}
                                                        className="p-1.5 rounded-lg text-zinc-500 hover:text-indigo-400 hover:bg-indigo-500/10 transition-all"
                                                        title="Descargar PDF"
                                                    ><Download className="w-3.5 h-3.5" /></button>
                                                    {albaran.status === "confirmed" && (
                                                        <button
                                                            onClick={() => handleConvertToInvoice(albaran)}
                                                            className="p-1.5 rounded-lg text-zinc-500 hover:text-emerald-400 hover:bg-emerald-500/10 transition-all"
                                                            title="Convertir a Factura"
                                                        ><FileEdit className="w-3.5 h-3.5" /></button>
                                                    )}
                                                    <button
                                                        onClick={() => handleDelete(albaran.id)}
                                                        className="p-1.5 rounded-lg text-zinc-500 hover:text-red-400 hover:bg-red-500/10 transition-all"
                                                        title="Eliminar"
                                                    ><Trash2 className="w-3.5 h-3.5" /></button>
                                                </div>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Modal */}
            {showModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
                    <div className="bg-[#111113] border border-[#27272a] rounded-2xl w-full max-w-3xl shadow-2xl flex flex-col max-h-[90vh]">
                        <div className="flex items-center justify-between p-6 border-b border-[#27272a]">
                            <h3 className="text-xl font-bold text-white">Nuevo Albarán</h3>
                            <button onClick={() => { setShowModal(false); resetModal(); }} className="text-zinc-500 hover:text-white transition">
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <form onSubmit={handleCreate} className="flex-1 overflow-auto p-6 space-y-5">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs text-zinc-400 mb-1">Cliente</label>
                                    <input value={clientName} onChange={e => setClientName(e.target.value)}
                                        placeholder="Nombre del cliente (opcional)"
                                        className="w-full px-3 py-2 rounded-lg bg-black/40 border border-[#3f3f46] text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-indigo-500/50" />
                                </div>
                                <div>
                                    <label className="block text-xs text-zinc-400 mb-1">Fecha</label>
                                    <input type="date" value={date} onChange={e => setDate(e.target.value)}
                                        className="w-full px-3 py-2 rounded-lg bg-black/40 border border-[#3f3f46] text-sm text-white focus:outline-none focus:border-indigo-500/50" />
                                </div>
                            </div>

                            {/* Lines */}
                            <div>
                                <div className="flex items-center justify-between mb-2">
                                    <label className="text-xs text-zinc-400">Líneas</label>
                                    <button type="button" onClick={() => setLines(prev => [...prev, emptyLine()])}
                                        className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition">
                                        <Plus className="w-3 h-3" /> Añadir línea
                                    </button>
                                </div>
                                <div className="space-y-2">
                                    <div className="grid grid-cols-12 gap-2 text-[10px] text-zinc-500 px-1">
                                        <span className="col-span-5">Descripción</span>
                                        <span className="col-span-2">Cantidad</span>
                                        <span className="col-span-2">Precio unit.</span>
                                        <span className="col-span-2">IVA %</span>
                                        <span className="col-span-1"></span>
                                    </div>
                                    {lines.map((line, i) => (
                                        <div key={i} className="grid grid-cols-12 gap-2 items-center">
                                            <input value={line.description} onChange={e => setLines(prev => prev.map((l, j) => j === i ? { ...l, description: e.target.value } : l))}
                                                placeholder="Descripción..." className="col-span-5 px-2 py-1.5 rounded-lg bg-black/40 border border-[#3f3f46] text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-indigo-500/50" />
                                            <input type="number" value={line.quantity} onChange={e => setLines(prev => prev.map((l, j) => j === i ? { ...l, quantity: e.target.value } : l))}
                                                className="col-span-2 px-2 py-1.5 rounded-lg bg-black/40 border border-[#3f3f46] text-xs text-white focus:outline-none focus:border-indigo-500/50" />
                                            <input type="number" value={line.unit_price} onChange={e => setLines(prev => prev.map((l, j) => j === i ? { ...l, unit_price: e.target.value } : l))}
                                                className="col-span-2 px-2 py-1.5 rounded-lg bg-black/40 border border-[#3f3f46] text-xs text-white focus:outline-none focus:border-indigo-500/50" />
                                            <input type="number" value={line.tax_percentage} onChange={e => setLines(prev => prev.map((l, j) => j === i ? { ...l, tax_percentage: e.target.value } : l))}
                                                className="col-span-2 px-2 py-1.5 rounded-lg bg-black/40 border border-[#3f3f46] text-xs text-white focus:outline-none focus:border-indigo-500/50" />
                                            <button type="button" onClick={() => lines.length > 1 && setLines(prev => prev.filter((_, j) => j !== i))}
                                                className="col-span-1 flex justify-center text-zinc-600 hover:text-red-400 transition">
                                                <X className="w-3.5 h-3.5" />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div>
                                <label className="block text-xs text-zinc-400 mb-1">Observaciones</label>
                                <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={2}
                                    placeholder="Notas adicionales (opcional)"
                                    className="w-full px-3 py-2 rounded-lg bg-black/40 border border-[#3f3f46] text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-indigo-500/50 resize-none" />
                            </div>

                            <div className="flex justify-end gap-3 pt-2">
                                <button type="button" onClick={() => { setShowModal(false); resetModal(); }}
                                    className="px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-white text-sm transition">
                                    Cancelar
                                </button>
                                <button type="submit" disabled={saving}
                                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium transition">
                                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                                    Crear Albarán
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
