"use client";

import { useEffect, useState } from "react";
import { api, type SalesOrder, type Client, type Product, type SalesOrderLine } from "@/lib/api";
import {
    ClipboardList, Plus, Search, Loader2, X, Pencil, Trash2,
    ChevronDown, Package, Calendar, Check
} from "lucide-react";

const fmt = (n: number) => n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });

const STATUS_MAP: Record<string, { label: string; color: string; bg: string; border: string }> = {
    draft: { label: "Borrador", color: "text-zinc-400", bg: "bg-zinc-500/10", border: "border-zinc-500/20" },
    confirmed: { label: "Confirmado", color: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/20" },
    processing: { label: "En proceso", color: "text-amber-400", bg: "bg-amber-500/10", border: "border-amber-500/20" },
    shipped: { label: "Enviado", color: "text-indigo-400", bg: "bg-indigo-500/10", border: "border-indigo-500/20" },
    delivered: { label: "Entregado", color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20" },
    cancelled: { label: "Cancelado", color: "text-rose-400", bg: "bg-rose-500/10", border: "border-rose-500/20" },
};

const STATUS_FLOW: Record<string, string> = {
    draft: "confirmed", confirmed: "processing", processing: "shipped", shipped: "delivered"
};

const EMPTY_LINE: SalesOrderLine = { description: "", quantity: 1, unit_price: 0, discount_percentage: 0, tax_percentage: 21 };

export default function PedidosPage() {
    const [orders, setOrders] = useState<SalesOrder[]>([]);
    const [clients, setClients] = useState<Client[]>([]);
    const [products, setProducts] = useState<Product[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [showModal, setShowModal] = useState(false);
    const [expandedId, setExpandedId] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const [deletingId, setDeletingId] = useState<string | null>(null);

    const [form, setForm] = useState({
        client_id: "",
        expected_delivery: "",
        notes: "",
        lines: [{ ...EMPTY_LINE }] as SalesOrderLine[],
    });

    const load = async () => {
        try {
            const [ordersData, clientsData, productsData] = await Promise.all([
                api.erp.orders.list(),
                api.erp.clients.list({ limit: 200 }),
                api.erp.products.list({ limit: 200 }),
            ]);
            setOrders(ordersData);
            setClients(clientsData.filter(c => c.client_type === "customer"));
            setProducts(productsData);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { load(); }, []);

    const openNew = () => {
        setForm({ client_id: "", expected_delivery: "", notes: "", lines: [{ ...EMPTY_LINE }] });
        setShowModal(true);
    };

    const setLine = (i: number, field: keyof SalesOrderLine, value: any) => {
        setForm(f => {
            const lines = [...f.lines];
            lines[i] = { ...lines[i], [field]: value };
            // Auto-fill description from product
            if (field === "product_id") {
                const prod = products.find(p => p.id === value);
                if (prod) {
                    lines[i].description = prod.name;
                    lines[i].unit_price = prod.price;
                    lines[i].tax_percentage = prod.tax_percentage;
                }
            }
            return { ...f, lines };
        });
    };

    const addLine = () => setForm(f => ({ ...f, lines: [...f.lines, { ...EMPTY_LINE }] }));
    const removeLine = (i: number) => setForm(f => ({ ...f, lines: f.lines.filter((_, idx) => idx !== i) }));

    const lineTotal = (line: SalesOrderLine) => {
        const base = line.quantity * line.unit_price * (1 - (line.discount_percentage || 0) / 100);
        return base * (1 + line.tax_percentage / 100);
    };

    const orderTotal = form.lines.reduce((acc, l) => acc + lineTotal(l), 0);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.client_id || form.lines.every(l => !l.description)) return;
        setSaving(true);
        try {
            await api.erp.orders.create({
                client_id: form.client_id,
                expected_delivery: form.expected_delivery || undefined,
                notes: form.notes || undefined,
                lines: form.lines.filter(l => l.description.trim()),
            } as any);
            setShowModal(false);
            setLoading(true);
            load();
        } catch (err) {
            console.error(err);
        } finally {
            setSaving(false);
        }
    };

    const handleAdvanceStatus = async (order: SalesOrder) => {
        const nextStatus = STATUS_FLOW[order.status];
        if (!nextStatus) return;
        try {
            const updated = await api.erp.orders.update(order.id, { status: nextStatus });
            setOrders(prev => prev.map(o => o.id === order.id ? updated : o));
        } catch (err) {
            console.error(err);
        }
    };

    const handleCancel = async (order: SalesOrder) => {
        if (!confirm("¿Cancelar este pedido?")) return;
        try {
            const updated = await api.erp.orders.update(order.id, { status: "cancelled" });
            setOrders(prev => prev.map(o => o.id === order.id ? updated : o));
        } catch (err) {
            console.error(err);
        }
    };

    const handleDelete = async (id: string) => {
        if (!confirm("¿Eliminar este pedido definitivamente?")) return;
        setDeletingId(id);
        try {
            await api.erp.orders.delete(id);
            setOrders(prev => prev.filter(o => o.id !== id));
        } catch (err) {
            console.error(err);
        } finally {
            setDeletingId(null);
        }
    };

    const q = search.toLowerCase();
    const filtered = orders.filter(o =>
        !q ||
        (o.order_number || "").toLowerCase().includes(q) ||
        (o.client?.name || "").toLowerCase().includes(q)
    );

    const byStatus = (s: string) => orders.filter(o => o.status === s).length;

    return (
        <div className="p-8 max-w-6xl mx-auto space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white tracking-tight">Pedidos de Venta</h1>
                    <p className="mt-1 text-sm text-zinc-400">Gestiona el flujo de pedidos de clientes antes de facturar.</p>
                </div>
                <button onClick={openNew} className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors">
                    <Plus className="w-4 h-4" /> Nuevo pedido
                </button>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-4">
                {[
                    { label: "Confirmados", value: byStatus("confirmed") + byStatus("processing"), color: "text-blue-400" },
                    { label: "En tránsito", value: byStatus("shipped"), color: "text-indigo-400" },
                    { label: "Entregados", value: byStatus("delivered"), color: "text-emerald-400" },
                ].map(stat => (
                    <div key={stat.label} className="bg-[#111113] border border-[#27272a] rounded-2xl p-5">
                        <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">{stat.label}</p>
                        <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
                    </div>
                ))}
            </div>

            {/* Search */}
            <div className="relative">
                <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                    type="text"
                    placeholder="Buscar por número o cliente..."
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    className="w-full bg-[#18181b] border border-[#3f3f46] text-white text-sm rounded-xl pl-9 pr-4 py-2.5 focus:outline-none focus:border-indigo-500 transition-colors"
                />
            </div>

            {/* Orders list */}
            {loading ? (
                <div className="flex items-center justify-center py-24 text-zinc-500 gap-2">
                    <Loader2 className="w-5 h-5 animate-spin" /> Cargando pedidos…
                </div>
            ) : filtered.length === 0 ? (
                <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-16 flex flex-col items-center text-center">
                    <ClipboardList className="w-12 h-12 text-zinc-700 mb-4" />
                    <h2 className="text-lg font-bold text-white mb-2">{orders.length === 0 ? "Sin pedidos" : "Sin resultados"}</h2>
                    <p className="text-sm text-zinc-500 max-w-md">
                        {orders.length === 0 ? "Crea tu primer pedido de venta." : `No hay pedidos que coincidan con "${search}"`}
                    </p>
                    {orders.length === 0 && (
                        <button onClick={openNew} className="mt-6 bg-indigo-600 hover:bg-indigo-500 text-white text-sm px-4 py-2 rounded-xl transition-colors">
                            Crear pedido
                        </button>
                    )}
                </div>
            ) : (
                <div className="space-y-3">
                    {filtered.map(order => {
                        const st = STATUS_MAP[order.status] || STATUS_MAP.draft;
                        const nextStatus = STATUS_FLOW[order.status];
                        const isExpanded = expandedId === order.id;

                        return (
                            <div key={order.id} className="bg-[#111113] border border-[#27272a] rounded-2xl overflow-hidden">
                                {/* Header row */}
                                <div className="flex items-center gap-4 px-6 py-4">
                                    <button onClick={() => setExpandedId(isExpanded ? null : order.id)} className="flex-1 flex items-center gap-4 text-left">
                                        <div className={`${st.bg} ${st.border} border rounded-xl p-2 flex-shrink-0`}>
                                            <ClipboardList className={`w-4 h-4 ${st.color}`} />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <p className="text-sm font-bold text-white font-mono">{order.order_number || "Sin número"}</p>
                                                <span className={`text-xs px-2 py-0.5 rounded-full ${st.bg} ${st.border} border ${st.color}`}>{st.label}</span>
                                            </div>
                                            <p className="text-xs text-zinc-500 mt-0.5">{order.client?.name || "Cliente desconocido"}</p>
                                        </div>
                                        <div className="text-right flex-shrink-0">
                                            <p className="text-sm font-bold text-white">{fmt(order.amount_total)}</p>
                                            <p className="text-xs text-zinc-600">{new Date(order.date).toLocaleDateString("es-ES")}</p>
                                        </div>
                                        <ChevronDown className={`w-4 h-4 text-zinc-500 transition-transform ${isExpanded ? "rotate-180" : ""}`} />
                                    </button>
                                    <div className="flex items-center gap-2 flex-shrink-0">
                                        {nextStatus && (
                                            <button
                                                onClick={() => handleAdvanceStatus(order)}
                                                className="flex items-center gap-1.5 bg-emerald-600/80 hover:bg-emerald-500 text-white text-xs px-3 py-1.5 rounded-lg transition-colors"
                                                title={`Pasar a ${STATUS_MAP[nextStatus]?.label}`}
                                            >
                                                <Check className="w-3 h-3" /> {STATUS_MAP[nextStatus]?.label}
                                            </button>
                                        )}
                                        {order.status !== "cancelled" && order.status !== "delivered" && (
                                            <button onClick={() => handleCancel(order)} className="text-xs text-zinc-500 hover:text-rose-400 px-2 py-1.5 rounded-lg hover:bg-rose-500/10 transition-colors">
                                                Cancelar
                                            </button>
                                        )}
                                        <button onClick={() => handleDelete(order.id)} disabled={deletingId === order.id} className="p-1.5 rounded-lg hover:bg-rose-500/10 text-zinc-600 hover:text-rose-400 transition-colors">
                                            {deletingId === order.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                                        </button>
                                    </div>
                                </div>

                                {/* Expanded lines */}
                                {isExpanded && (
                                    <div className="border-t border-[#27272a]/50 px-6 py-4 bg-[#161618]/40">
                                        {order.expected_delivery && (
                                            <p className="text-xs text-zinc-500 mb-3 flex items-center gap-1.5">
                                                <Calendar className="w-3 h-3" /> Entrega prevista: {new Date(order.expected_delivery).toLocaleDateString("es-ES")}
                                            </p>
                                        )}
                                        <div className="space-y-2">
                                            {(order.lines || []).map((line, i) => (
                                                <div key={i} className="flex items-center gap-4 text-sm">
                                                    <Package className="w-3.5 h-3.5 text-zinc-600 flex-shrink-0" />
                                                    <span className="flex-1 text-zinc-300">{line.description}</span>
                                                    <span className="text-zinc-500 font-mono">{line.quantity} × {fmt(line.unit_price)}</span>
                                                    <span className="text-zinc-400 font-mono w-24 text-right">{fmt((line.total || 0))}</span>
                                                </div>
                                            ))}
                                        </div>
                                        {order.notes && (
                                            <p className="text-xs text-zinc-600 mt-3 italic">{order.notes}</p>
                                        )}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Create Modal */}
            {showModal && (
                <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 backdrop-blur-sm pt-16 pb-8 overflow-y-auto">
                    <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-8 w-full max-w-2xl shadow-2xl">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-lg font-bold text-white">Nuevo pedido de venta</h2>
                            <button onClick={() => setShowModal(false)} className="text-zinc-500 hover:text-white transition-colors">
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <form onSubmit={handleSubmit} className="space-y-6">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs text-zinc-400 mb-1.5 font-medium">Cliente *</label>
                                    <select
                                        required value={form.client_id}
                                        onChange={e => setForm(f => ({ ...f, client_id: e.target.value }))}
                                        className="w-full bg-[#18181b] border border-[#3f3f46] text-white text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-indigo-500 transition-colors"
                                    >
                                        <option value="">Seleccionar cliente…</option>
                                        {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs text-zinc-400 mb-1.5 font-medium">Entrega prevista</label>
                                    <input
                                        type="date" value={form.expected_delivery}
                                        onChange={e => setForm(f => ({ ...f, expected_delivery: e.target.value }))}
                                        className="w-full bg-[#18181b] border border-[#3f3f46] text-white text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-indigo-500 transition-colors"
                                    />
                                </div>
                            </div>

                            {/* Lines */}
                            <div>
                                <div className="flex items-center justify-between mb-3">
                                    <p className="text-sm font-semibold text-white">Líneas del pedido</p>
                                    <button type="button" onClick={addLine} className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition-colors">
                                        <Plus className="w-3 h-3" /> Añadir línea
                                    </button>
                                </div>
                                <div className="space-y-3">
                                    {form.lines.map((line, i) => (
                                        <div key={i} className="grid grid-cols-12 gap-2 items-end bg-[#161618] rounded-xl p-3">
                                            <div className="col-span-5">
                                                <label className="block text-xs text-zinc-500 mb-1">Producto / Descripción</label>
                                                <select
                                                    value={line.product_id || ""}
                                                    onChange={e => setLine(i, "product_id" as any, e.target.value || null)}
                                                    className="w-full bg-[#18181b] border border-[#3f3f46] text-white text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-indigo-500 mb-1"
                                                >
                                                    <option value="">Seleccionar producto…</option>
                                                    {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                                                </select>
                                                <input
                                                    type="text" placeholder="Descripción" value={line.description}
                                                    onChange={e => setLine(i, "description", e.target.value)}
                                                    className="w-full bg-[#18181b] border border-[#3f3f46] text-white text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-indigo-500"
                                                />
                                            </div>
                                            <div className="col-span-2">
                                                <label className="block text-xs text-zinc-500 mb-1">Cant.</label>
                                                <input
                                                    type="number" min={0.01} step={0.01} value={line.quantity}
                                                    onChange={e => setLine(i, "quantity", parseFloat(e.target.value) || 0)}
                                                    className="w-full bg-[#18181b] border border-[#3f3f46] text-white text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-indigo-500"
                                                />
                                            </div>
                                            <div className="col-span-2">
                                                <label className="block text-xs text-zinc-500 mb-1">Precio</label>
                                                <input
                                                    type="number" min={0} step={0.01} value={line.unit_price}
                                                    onChange={e => setLine(i, "unit_price", parseFloat(e.target.value) || 0)}
                                                    className="w-full bg-[#18181b] border border-[#3f3f46] text-white text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-indigo-500"
                                                />
                                            </div>
                                            <div className="col-span-2">
                                                <label className="block text-xs text-zinc-500 mb-1">IVA %</label>
                                                <select
                                                    value={line.tax_percentage}
                                                    onChange={e => setLine(i, "tax_percentage", parseFloat(e.target.value))}
                                                    className="w-full bg-[#18181b] border border-[#3f3f46] text-white text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-indigo-500"
                                                >
                                                    {[0, 4, 10, 21].map(t => <option key={t} value={t}>{t}%</option>)}
                                                </select>
                                            </div>
                                            <div className="col-span-1 flex items-end justify-end">
                                                <button type="button" onClick={() => removeLine(i)} disabled={form.lines.length === 1} className="p-2 rounded-lg hover:bg-rose-500/10 text-zinc-600 hover:text-rose-400 transition-colors disabled:opacity-30">
                                                    <X className="w-3.5 h-3.5" />
                                                </button>
                                            </div>
                                            <div className="col-span-12 text-right text-xs text-zinc-500">
                                                Total línea: <span className="text-zinc-300 font-mono">{fmt(lineTotal(line))}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="bg-[#161618] rounded-xl p-4 flex items-center justify-between">
                                <span className="text-sm text-zinc-400">Total pedido</span>
                                <span className="text-xl font-bold text-white">{fmt(orderTotal)}</span>
                            </div>

                            <div>
                                <label className="block text-xs text-zinc-400 mb-1.5 font-medium">Notas internas</label>
                                <textarea
                                    value={form.notes} rows={2}
                                    onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                                    className="w-full bg-[#18181b] border border-[#3f3f46] text-white text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-indigo-500 transition-colors resize-none"
                                    placeholder="Instrucciones de entrega, notas al cliente..."
                                />
                            </div>

                            <div className="flex gap-3">
                                <button type="button" onClick={() => setShowModal(false)} className="flex-1 py-2.5 rounded-xl border border-[#3f3f46] text-zinc-400 text-sm hover:bg-white/5 transition-colors">
                                    Cancelar
                                </button>
                                <button type="submit" disabled={saving} className="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2">
                                    {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                                    Crear pedido
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
