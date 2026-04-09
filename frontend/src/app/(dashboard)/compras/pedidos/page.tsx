"use client";

import { useEffect, useState } from "react";
import { api, type PurchaseOrder, type Client, type Product, type PurchaseOrderLine } from "@/lib/api";
import {
    ShoppingBag, Plus, Search, Loader2, X, Trash2,
    ChevronDown, Package, Calendar, Check, Truck
} from "lucide-react";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";

const fmt = (n: number) => n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });

const STATUS_MAP: Record<string, { label: string; color: string; bg: string; border: string }> = {
    draft: { label: "Borrador", color: "text-muted-foreground", bg: "bg-muted", border: "border-border" },
    sent: { label: "Enviado", color: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/20" },
    confirmed: { label: "Confirmado", color: "text-primary", bg: "bg-primary/10", border: "border-primary/20" },
    received: { label: "Recibido", color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20" },
    cancelled: { label: "Cancelado", color: "text-rose-400", bg: "bg-rose-500/10", border: "border-rose-500/20" },
};

const STATUS_FLOW: Record<string, string> = {
    draft: "sent", sent: "confirmed", confirmed: "received"
};

const EMPTY_LINE: PurchaseOrderLine = { description: "", quantity: 1, unit_price: 0, tax_percentage: 21 };

export default function PedidosCompraPage() {
    const [orders, setOrders] = useState<PurchaseOrder[]>([]);
    const [suppliers, setSuppliers] = useState<Client[]>([]);
    const [products, setProducts] = useState<Product[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [showModal, setShowModal] = useState(false);
    const [expandedId, setExpandedId] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const [deletingId, setDeletingId] = useState<string | null>(null);

    const [form, setForm] = useState({
        supplier_id: "",
        expected_delivery: "",
        notes: "",
        lines: [{ ...EMPTY_LINE }] as PurchaseOrderLine[],
    });

    const load = async () => {
        try {
            const [ordersData, suppliersData, productsData] = await Promise.all([
                api.erp.purchaseOrders.list(),
                api.erp.clients.list({ client_type: "supplier", limit: 200 }),
                api.erp.products.list({ limit: 200 }),
            ]);
            setOrders(ordersData);
            setSuppliers(suppliersData);
            setProducts(productsData);
        } catch (err) { logError("compras/pedidos/page", err); }
        finally { setLoading(false); }
    };

    useEffect(() => { load(); }, []);

    const openNew = () => {
        setForm({ supplier_id: "", expected_delivery: "", notes: "", lines: [{ ...EMPTY_LINE }] });
        setShowModal(true);
    };

    const setLine = (i: number, field: keyof PurchaseOrderLine, value: any) => {
        setForm(f => {
            const lines = [...f.lines];
            lines[i] = { ...lines[i], [field]: value };
            if (field === "product_id") {
                const prod = products.find(p => p.id === value);
                if (prod) { lines[i].description = prod.name; lines[i].unit_price = prod.price; lines[i].tax_percentage = prod.tax_percentage; }
            }
            return { ...f, lines };
        });
    };

    const lineTotal = (line: PurchaseOrderLine) => {
        const base = line.quantity * line.unit_price;
        return base * (1 + line.tax_percentage / 100);
    };
    const orderTotal = form.lines.reduce((acc, l) => acc + lineTotal(l), 0);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.supplier_id) return;
        setSaving(true);
        try {
            await api.erp.purchaseOrders.create({
                supplier_id: form.supplier_id,
                expected_delivery: form.expected_delivery || undefined,
                notes: form.notes || undefined,
                lines: form.lines.filter(l => l.description.trim()),
            } as any);
            setShowModal(false);
            setLoading(true);
            load();
        } catch (err) { logError("compras/pedidos/page", err); }
        finally { setSaving(false); }
    };

    const handleAdvance = async (order: PurchaseOrder) => {
        const next = STATUS_FLOW[order.status];
        if (!next) return;
        try {
            const updated = await api.erp.purchaseOrders.update(order.id, { status: next });
            setOrders(prev => prev.map(o => o.id === order.id ? updated : o));
        } catch (err) { logError("compras/pedidos/page", err); }
    };

    const handleCancel = async (order: PurchaseOrder) => {
        if (!await showConfirm({ message: "¿Cancelar este pedido?", confirmLabel: "Cancelar", confirmVariant: "danger" })) return;
        try {
            const updated = await api.erp.purchaseOrders.update(order.id, { status: "cancelled" });
            setOrders(prev => prev.map(o => o.id === order.id ? updated : o));
        } catch (err) { logError("compras/pedidos/page", err); }
    };

    const handleDelete = async (id: string) => {
        if (!await showConfirm({ message: "¿Eliminar definitivamente?", confirmLabel: "Eliminar", confirmVariant: "danger" })) return;
        setDeletingId(id);
        try {
            await api.erp.purchaseOrders.delete(id);
            setOrders(prev => prev.filter(o => o.id !== id));
        } catch (err) { logError("compras/pedidos/page", err); }
        finally { setDeletingId(null); }
    };

    const q = search.toLowerCase();
    const filtered = orders.filter(o => !q || (o.order_number || "").toLowerCase().includes(q) || (o.supplier?.name || "").toLowerCase().includes(q));

    return (
        <div className="p-8 max-w-6xl mx-auto space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-foreground tracking-tight">Pedidos de Compra</h1>
                    <p className="mt-1 text-sm text-muted-foreground">Gestiona los pedidos a tus proveedores antes de recibir la factura.</p>
                </div>
                <button onClick={openNew} className="flex items-center gap-2 bg-primary hover:bg-primary text-foreground text-sm font-medium px-4 py-2.5 rounded-xl transition-colors">
                    <Plus className="w-4 h-4" /> Nuevo pedido
                </button>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-4">
                {[
                    { label: "Pendientes de recibir", value: orders.filter(o => ["sent", "confirmed"].includes(o.status)).length, color: "text-amber-400" },
                    { label: "Recibidos", value: orders.filter(o => o.status === "received").length, color: "text-emerald-400" },
                    { label: "Total comprometido", value: fmt(orders.filter(o => o.status !== "cancelled").reduce((a, o) => a + o.amount_total, 0)), color: "text-foreground" },
                ].map(stat => (
                    <div key={stat.label} className="bg-card border border-border rounded-2xl p-5">
                        <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">{stat.label}</p>
                        <p className={`text-xl font-bold ${stat.color}`}>{stat.value}</p>
                    </div>
                ))}
            </div>

            {/* Search */}
            <div className="relative">
                <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                    type="text" placeholder="Buscar por número o proveedor..."
                    value={search} onChange={e => setSearch(e.target.value)}
                    className="w-full bg-card border border-border text-foreground text-sm rounded-xl pl-9 pr-4 py-2.5 focus:outline-none focus:border-primary transition-colors"
                />
            </div>

            {/* List */}
            {loading ? (
                <div className="flex items-center justify-center py-24 text-muted-foreground gap-2">
                    <Loader2 className="w-5 h-5 animate-spin" /> Cargando pedidos…
                </div>
            ) : filtered.length === 0 ? (
                <div className="bg-card border border-border rounded-2xl p-16 flex flex-col items-center text-center">
                    <ShoppingBag className="w-12 h-12 text-muted-foreground mb-4" />
                    <h2 className="text-lg font-bold text-foreground mb-2">{orders.length === 0 ? "Sin pedidos de compra" : "Sin resultados"}</h2>
                    <p className="text-sm text-muted-foreground max-w-sm">
                        {orders.length === 0 ? "Crea tu primer pedido de compra a un proveedor." : `Sin resultados para "${search}"`}
                    </p>
                    {orders.length === 0 && (
                        <button onClick={openNew} className="mt-6 bg-primary hover:bg-primary text-foreground text-sm px-4 py-2 rounded-xl transition-colors">Crear pedido</button>
                    )}
                </div>
            ) : (
                <div className="space-y-3">
                    {filtered.map(order => {
                        const st = STATUS_MAP[order.status] || STATUS_MAP.draft;
                        const nextStatus = STATUS_FLOW[order.status];
                        const isExpanded = expandedId === order.id;

                        return (
                            <div key={order.id} className="bg-card border border-border rounded-2xl overflow-hidden">
                                <div className="flex items-center gap-4 px-6 py-4">
                                    <button onClick={() => setExpandedId(isExpanded ? null : order.id)} className="flex-1 flex items-center gap-4 text-left">
                                        <div className={`${st.bg} ${st.border} border rounded-xl p-2 flex-shrink-0`}>
                                            <Truck className={`w-4 h-4 ${st.color}`} />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <p className="text-sm font-bold text-foreground font-mono">{order.order_number || "Sin número"}</p>
                                                <span className={`text-xs px-2 py-0.5 rounded-full ${st.bg} ${st.border} border ${st.color}`}>{st.label}</span>
                                            </div>
                                            <p className="text-xs text-muted-foreground mt-0.5">{order.supplier?.name || "Proveedor desconocido"}</p>
                                        </div>
                                        <div className="text-right flex-shrink-0">
                                            <p className="text-sm font-bold text-foreground">{fmt(order.amount_total)}</p>
                                            <p className="text-xs text-muted-foreground">{new Date(order.date).toLocaleDateString("es-ES")}</p>
                                        </div>
                                        <ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform ${isExpanded ? "rotate-180" : ""}`} />
                                    </button>
                                    <div className="flex items-center gap-2 flex-shrink-0">
                                        {nextStatus && (
                                            <button onClick={() => handleAdvance(order)} className="flex items-center gap-1.5 bg-emerald-600/80 hover:bg-emerald-500 text-foreground text-xs px-3 py-1.5 rounded-lg transition-colors">
                                                <Check className="w-3 h-3" /> {STATUS_MAP[nextStatus]?.label}
                                            </button>
                                        )}
                                        {!["cancelled", "received"].includes(order.status) && (
                                            <button onClick={() => handleCancel(order)} className="text-xs text-muted-foreground hover:text-rose-400 px-2 py-1.5 rounded-lg hover:bg-rose-500/10 transition-colors">Cancelar</button>
                                        )}
                                        <button onClick={() => handleDelete(order.id)} disabled={deletingId === order.id} className="p-1.5 rounded-lg hover:bg-rose-500/10 text-muted-foreground hover:text-rose-400 transition-colors">
                                            {deletingId === order.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                                        </button>
                                    </div>
                                </div>

                                {isExpanded && (
                                    <div className="border-t border-border/50 px-6 py-4 bg-muted/40">
                                        {order.expected_delivery && (
                                            <p className="text-xs text-muted-foreground mb-3 flex items-center gap-1.5">
                                                <Calendar className="w-3 h-3" /> Entrega prevista: {new Date(order.expected_delivery).toLocaleDateString("es-ES")}
                                            </p>
                                        )}
                                        <div className="space-y-2">
                                            {(order.lines || []).map((line, i) => (
                                                <div key={i} className="flex items-center gap-4 text-sm">
                                                    <Package className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                                                    <span className="flex-1 text-foreground">{line.description}</span>
                                                    <span className="text-muted-foreground font-mono">{line.quantity} × {fmt(line.unit_price)}</span>
                                                    <span className="text-muted-foreground font-mono w-24 text-right">{fmt(line.total || 0)}</span>
                                                </div>
                                            ))}
                                        </div>
                                        {order.notes && <p className="text-xs text-muted-foreground mt-3 italic">{order.notes}</p>}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Modal */}
            {showModal && (
                <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 backdrop-blur-sm pt-16 pb-8 overflow-y-auto">
                    <div className="bg-card border border-border rounded-2xl p-8 w-full max-w-2xl shadow-2xl">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-lg font-bold text-foreground">Nuevo pedido de compra</h2>
                            <button onClick={() => setShowModal(false)} className="text-muted-foreground hover:text-foreground transition-colors"><X className="w-5 h-5" /></button>
                        </div>
                        <form onSubmit={handleSubmit} className="space-y-6">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs text-muted-foreground mb-1.5 font-medium">Proveedor *</label>
                                    <select required value={form.supplier_id} onChange={e => setForm(f => ({ ...f, supplier_id: e.target.value }))}
                                        className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors">
                                        <option value="">Seleccionar proveedor…</option>
                                        {suppliers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                                    </select>
                                    {suppliers.length === 0 && <p className="text-xs text-amber-400 mt-1">Crea proveedores en Compras → Proveedores</p>}
                                </div>
                                <div>
                                    <label className="block text-xs text-muted-foreground mb-1.5 font-medium">Entrega prevista</label>
                                    <input type="date" value={form.expected_delivery} onChange={e => setForm(f => ({ ...f, expected_delivery: e.target.value }))}
                                        className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors" />
                                </div>
                            </div>

                            {/* Lines */}
                            <div>
                                <div className="flex items-center justify-between mb-3">
                                    <p className="text-sm font-semibold text-foreground">Líneas del pedido</p>
                                    <button type="button" onClick={() => setForm(f => ({ ...f, lines: [...f.lines, { ...EMPTY_LINE }] }))}
                                        className="text-xs text-primary hover:text-primary flex items-center gap-1 transition-colors">
                                        <Plus className="w-3 h-3" /> Añadir
                                    </button>
                                </div>
                                <div className="space-y-2">
                                    {form.lines.map((line, i) => (
                                        <div key={i} className="grid grid-cols-12 gap-2 items-end bg-muted rounded-xl p-3">
                                            <div className="col-span-5">
                                                <label className="block text-xs text-muted-foreground mb-1">Producto / Descripción</label>
                                                <select value={(line as any).product_id || ""} onChange={e => setLine(i, "product_id" as any, e.target.value || null)}
                                                    className="w-full bg-card border border-border text-foreground text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-primary mb-1">
                                                    <option value="">Seleccionar…</option>
                                                    {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                                                </select>
                                                <input type="text" placeholder="Descripción" value={line.description} onChange={e => setLine(i, "description", e.target.value)}
                                                    className="w-full bg-card border border-border text-foreground text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-primary" />
                                            </div>
                                            <div className="col-span-2">
                                                <label className="block text-xs text-muted-foreground mb-1">Cant.</label>
                                                <input type="number" min={0.01} step={0.01} value={line.quantity} onChange={e => setLine(i, "quantity", parseFloat(e.target.value) || 0)}
                                                    className="w-full bg-card border border-border text-foreground text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-primary" />
                                            </div>
                                            <div className="col-span-2">
                                                <label className="block text-xs text-muted-foreground mb-1">Precio</label>
                                                <input type="number" min={0} step={0.01} value={line.unit_price} onChange={e => setLine(i, "unit_price", parseFloat(e.target.value) || 0)}
                                                    className="w-full bg-card border border-border text-foreground text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-primary" />
                                            </div>
                                            <div className="col-span-2">
                                                <label className="block text-xs text-muted-foreground mb-1">IVA %</label>
                                                <select value={line.tax_percentage} onChange={e => setLine(i, "tax_percentage", parseFloat(e.target.value))}
                                                    className="w-full bg-card border border-border text-foreground text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-primary">
                                                    {[0, 4, 10, 21].map(t => <option key={t} value={t}>{t}%</option>)}
                                                </select>
                                            </div>
                                            <div className="col-span-1 flex items-end justify-end">
                                                <button type="button" onClick={() => setForm(f => ({ ...f, lines: f.lines.filter((_, idx) => idx !== i) }))} disabled={form.lines.length === 1}
                                                    className="p-2 rounded-lg hover:bg-rose-500/10 text-muted-foreground hover:text-rose-400 transition-colors disabled:opacity-30">
                                                    <X className="w-3.5 h-3.5" />
                                                </button>
                                            </div>
                                            <div className="col-span-12 text-right text-xs text-muted-foreground">
                                                Total: <span className="text-foreground font-mono">{fmt(lineTotal(line))}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="bg-muted rounded-xl p-4 flex items-center justify-between">
                                <span className="text-sm text-muted-foreground">Total pedido</span>
                                <span className="text-xl font-bold text-foreground">{fmt(orderTotal)}</span>
                            </div>

                            <div>
                                <label className="block text-xs text-muted-foreground mb-1.5 font-medium">Notas</label>
                                <textarea value={form.notes} rows={2} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                                    className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors resize-none"
                                    placeholder="Condiciones especiales, instrucciones de entrega..." />
                            </div>

                            <div className="flex gap-3">
                                <button type="button" onClick={() => setShowModal(false)} className="flex-1 py-2.5 rounded-xl border border-border text-muted-foreground text-sm hover:bg-accent/50 transition-colors">Cancelar</button>
                                <button type="submit" disabled={saving} className="flex-1 py-2.5 rounded-xl bg-primary hover:bg-primary text-foreground text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2">
                                    {saving && <Loader2 className="w-4 h-4 animate-spin" />} Crear pedido
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
