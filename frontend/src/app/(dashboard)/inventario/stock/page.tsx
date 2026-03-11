"use client";

import { useEffect, useState } from "react";
import { api, type Product, type StockMovement } from "@/lib/api";
import {
    Package, Plus, Search, ArrowUpCircle, ArrowDownCircle, SlidersHorizontal,
    Loader2, X, AlertTriangle, ChevronDown, ChevronUp, Clock
} from "lucide-react";
import { useToastStore } from "@/stores/toast";

const fmt = (n: number) => n.toLocaleString("es-ES");

const MOVEMENT_ICONS: Record<string, React.ReactNode> = {
    entrada: <ArrowUpCircle className="w-4 h-4 text-emerald-400" />,
    salida: <ArrowDownCircle className="w-4 h-4 text-rose-400" />,
    ajuste: <SlidersHorizontal className="w-4 h-4 text-amber-400" />,
};

const MOVEMENT_COLORS: Record<string, string> = {
    entrada: "text-emerald-400",
    salida: "text-rose-400",
    ajuste: "text-amber-400",
};

interface MovementForm {
    movement_type: "entrada" | "salida" | "ajuste";
    quantity: number;
    reference: string;
    notes: string;
}

export default function StockPage() {
    const toast = useToastStore();
    const [products, setProducts] = useState<Product[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [expandedId, setExpandedId] = useState<string | null>(null);
    const [movements, setMovements] = useState<Record<string, StockMovement[]>>({});
    const [movementsLoading, setMovementsLoading] = useState<string | null>(null);

    const [showModal, setShowModal] = useState(false);
    const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
    const [movForm, setMovForm] = useState<MovementForm>({ movement_type: "entrada", quantity: 1, reference: "", notes: "" });
    const [saving, setSaving] = useState(false);

    const load = () =>
        api.erp.products.list({ limit: 200 })
            .then(data => setProducts(data.filter(p => p.item_type === "product")))
            .catch(console.error)
            .finally(() => setLoading(false));

    useEffect(() => { load(); }, []);

    const toggleExpand = async (productId: string) => {
        if (expandedId === productId) {
            setExpandedId(null);
            return;
        }
        setExpandedId(productId);
        if (!movements[productId]) {
            setMovementsLoading(productId);
            try {
                const movs = await api.erp.stock.movements(productId);
                setMovements(prev => ({ ...prev, [productId]: movs }));
            } catch (err) {
                console.error(err);
            } finally {
                setMovementsLoading(null);
            }
        }
    };

    const openMovement = (product: Product) => {
        setSelectedProduct(product);
        setMovForm({ movement_type: "entrada", quantity: 1, reference: "", notes: "" });
        setShowModal(true);
    };

    const handleMovement = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedProduct) return;
        setSaving(true);
        try {
            await api.erp.stock.addMovement(selectedProduct.id, movForm);
            setShowModal(false);
            // Recargar productos y movimientos del producto
            load();
            if (movements[selectedProduct.id]) {
                const movs = await api.erp.stock.movements(selectedProduct.id);
                setMovements(prev => ({ ...prev, [selectedProduct.id]: movs }));
            }
        } catch (err: any) {
            toast.error(err?.message || "Error al registrar movimiento");
        } finally {
            setSaving(false);
        }
    };

    const q = search.toLowerCase();
    const filtered = products.filter(p => !q || p.name.toLowerCase().includes(q) || (p.sku || "").toLowerCase().includes(q));

    const totalStock = products.reduce((acc, p) => acc + (p.stock_quantity || 0), 0);
    const lowStock = products.filter(p => p.stock_min_alert > 0 && p.stock_quantity <= p.stock_min_alert).length;
    const outOfStock = products.filter(p => p.stock_quantity === 0).length;

    return (
        <div className="p-8 max-w-6xl mx-auto space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white tracking-tight">Control de Stock</h1>
                    <p className="mt-1 text-sm text-zinc-400">Gestiona el inventario físico de tus productos con entradas, salidas y ajustes.</p>
                </div>
            </div>

            {/* KPIs */}
            <div className="grid grid-cols-3 gap-4">
                <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-5">
                    <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Unidades en stock</p>
                    <p className="text-2xl font-bold text-white">{fmt(totalStock)}</p>
                </div>
                <div className={`rounded-2xl p-5 border ${lowStock > 0 ? "bg-amber-500/10 border-amber-500/20" : "bg-[#111113] border-[#27272a]"}`}>
                    <p className={`text-xs uppercase tracking-wider mb-1 ${lowStock > 0 ? "text-amber-400" : "text-zinc-500"}`}>Stock bajo</p>
                    <p className={`text-2xl font-bold ${lowStock > 0 ? "text-amber-400" : "text-white"}`}>{lowStock} productos</p>
                </div>
                <div className={`rounded-2xl p-5 border ${outOfStock > 0 ? "bg-rose-500/10 border-rose-500/20" : "bg-[#111113] border-[#27272a]"}`}>
                    <p className={`text-xs uppercase tracking-wider mb-1 ${outOfStock > 0 ? "text-rose-400" : "text-zinc-500"}`}>Sin stock</p>
                    <p className={`text-2xl font-bold ${outOfStock > 0 ? "text-rose-400" : "text-white"}`}>{outOfStock} productos</p>
                </div>
            </div>

            {/* Search */}
            <div className="relative">
                <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                    type="text"
                    placeholder="Buscar producto o SKU..."
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    className="w-full bg-[#18181b] border border-[#3f3f46] text-white text-sm rounded-xl pl-9 pr-4 py-2.5 focus:outline-none focus:border-indigo-500 transition-colors"
                />
            </div>

            {/* Product list */}
            {loading ? (
                <div className="flex items-center justify-center py-24 text-zinc-500 gap-2">
                    <Loader2 className="w-5 h-5 animate-spin" /> Cargando inventario…
                </div>
            ) : filtered.length === 0 ? (
                <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-16 flex flex-col items-center text-center">
                    <Package className="w-12 h-12 text-zinc-700 mb-4" />
                    <h2 className="text-lg font-bold text-white mb-2">Sin productos físicos</h2>
                    <p className="text-sm text-zinc-500 max-w-md">
                        Añade productos en el catálogo para gestionar su stock aquí.
                    </p>
                </div>
            ) : (
                <div className="bg-[#111113] border border-[#27272a] rounded-2xl overflow-hidden">
                    {/* Header */}
                    <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#27272a] text-xs font-medium text-zinc-500 uppercase tracking-wide bg-[#161618]">
                        <div className="col-span-4">Producto</div>
                        <div className="col-span-2 text-center">Stock actual</div>
                        <div className="col-span-2 text-center">Alerta mínima</div>
                        <div className="col-span-2 text-center">Estado</div>
                        <div className="col-span-2 text-right">Acción</div>
                    </div>
                    {filtered.map(product => {
                        const isLow = product.stock_min_alert > 0 && product.stock_quantity <= product.stock_min_alert;
                        const isOut = product.stock_quantity === 0;
                        const isExpanded = expandedId === product.id;

                        return (
                            <div key={product.id} className="border-b border-[#27272a]/50 last:border-0">
                                <div className="grid grid-cols-12 gap-4 px-6 py-3.5 hover:bg-white/[0.02] transition-colors items-center">
                                    <div className="col-span-4 flex items-center gap-3">
                                        <div className="w-8 h-8 rounded-lg bg-[#27272a] flex items-center justify-center flex-shrink-0">
                                            <Package className="w-4 h-4 text-zinc-400" />
                                        </div>
                                        <div>
                                            <p className="text-sm font-medium text-white">{product.name}</p>
                                            {product.sku && <p className="text-xs text-zinc-600 font-mono">{product.sku}</p>}
                                        </div>
                                    </div>
                                    <div className="col-span-2 text-center">
                                        <span className={`text-lg font-bold font-mono ${isOut ? "text-rose-400" : isLow ? "text-amber-400" : "text-white"}`}>
                                            {fmt(product.stock_quantity)}
                                        </span>
                                    </div>
                                    <div className="col-span-2 text-center">
                                        <span className="text-sm text-zinc-500 font-mono">
                                            {product.stock_min_alert > 0 ? fmt(product.stock_min_alert) : "—"}
                                        </span>
                                    </div>
                                    <div className="col-span-2 text-center">
                                        {isOut ? (
                                            <span className="bg-rose-500/10 text-rose-400 border border-rose-500/20 text-xs px-2.5 py-1 rounded-full">Sin stock</span>
                                        ) : isLow ? (
                                            <span className="bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xs px-2.5 py-1 rounded-full flex items-center gap-1 justify-center">
                                                <AlertTriangle className="w-3 h-3" /> Stock bajo
                                            </span>
                                        ) : (
                                            <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs px-2.5 py-1 rounded-full">OK</span>
                                        )}
                                    </div>
                                    <div className="col-span-2 flex items-center justify-end gap-2">
                                        <button
                                            onClick={() => openMovement(product)}
                                            className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs px-3 py-1.5 rounded-lg transition-colors"
                                        >
                                            <Plus className="w-3 h-3" /> Movimiento
                                        </button>
                                        <button
                                            onClick={() => toggleExpand(product.id)}
                                            className="p-1.5 rounded-lg hover:bg-white/10 text-zinc-500 hover:text-white transition-colors"
                                        >
                                            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                                        </button>
                                    </div>
                                </div>

                                {/* Movements panel */}
                                {isExpanded && (
                                    <div className="bg-[#161618]/50 border-t border-[#27272a]/50 px-6 py-4">
                                        <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">Historial de movimientos</p>
                                        {movementsLoading === product.id ? (
                                            <div className="flex items-center gap-2 text-zinc-500 text-sm py-2">
                                                <Loader2 className="w-4 h-4 animate-spin" /> Cargando…
                                            </div>
                                        ) : !movements[product.id] || movements[product.id].length === 0 ? (
                                            <p className="text-zinc-600 text-sm italic">Sin movimientos registrados.</p>
                                        ) : (
                                            <div className="space-y-2">
                                                {movements[product.id].slice(0, 10).map(mov => (
                                                    <div key={mov.id} className="flex items-center gap-3 text-sm">
                                                        {MOVEMENT_ICONS[mov.movement_type]}
                                                        <span className={`font-medium w-14 ${MOVEMENT_COLORS[mov.movement_type]}`}>
                                                            {mov.movement_type === "entrada" ? "+" : mov.movement_type === "salida" ? "-" : "="}{Math.abs(mov.quantity)}
                                                        </span>
                                                        <span className="text-zinc-400 flex-1">{mov.reference || mov.notes || <span className="italic text-zinc-600">Sin referencia</span>}</span>
                                                        <span className="text-zinc-600 font-mono text-xs">→ {fmt(mov.stock_after)} uds.</span>
                                                        <span className="text-zinc-700 text-xs flex items-center gap-1">
                                                            <Clock className="w-3 h-3" />
                                                            {new Date(mov.created_at).toLocaleDateString("es-ES")}
                                                        </span>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Movement modal */}
            {showModal && selectedProduct && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
                    <div className="bg-[#111113] border border-[#27272a] rounded-2xl p-8 w-full max-w-md shadow-2xl">
                        <div className="flex items-center justify-between mb-6">
                            <div>
                                <h2 className="text-lg font-bold text-white">Registrar movimiento</h2>
                                <p className="text-sm text-zinc-500 mt-0.5">{selectedProduct.name} · Stock actual: <span className="text-white font-mono">{fmt(selectedProduct.stock_quantity)}</span></p>
                            </div>
                            <button onClick={() => setShowModal(false)} className="text-zinc-500 hover:text-white transition-colors">
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <form onSubmit={handleMovement} className="space-y-4">
                            <div>
                                <label className="block text-xs text-zinc-400 mb-1.5 font-medium">Tipo de movimiento</label>
                                <div className="grid grid-cols-3 gap-2">
                                    {(["entrada", "salida", "ajuste"] as const).map(type => (
                                        <button
                                            key={type}
                                            type="button"
                                            onClick={() => setMovForm(f => ({ ...f, movement_type: type }))}
                                            className={`py-2.5 rounded-xl text-sm font-medium border transition-colors capitalize ${movForm.movement_type === type
                                                ? type === "entrada" ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-400"
                                                    : type === "salida" ? "bg-rose-500/20 border-rose-500/40 text-rose-400"
                                                        : "bg-amber-500/20 border-amber-500/40 text-amber-400"
                                                : "bg-[#18181b] border-[#3f3f46] text-zinc-400 hover:border-zinc-500"
                                                }`}
                                        >
                                            {type}
                                        </button>
                                    ))}
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs text-zinc-400 mb-1.5 font-medium">
                                    {movForm.movement_type === "ajuste" ? "Nuevo stock total" : "Cantidad"}
                                </label>
                                <input
                                    type="number" required min={1} value={movForm.quantity}
                                    onChange={e => setMovForm(f => ({ ...f, quantity: parseInt(e.target.value) || 0 }))}
                                    className="w-full bg-[#18181b] border border-[#3f3f46] text-white text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-indigo-500 transition-colors"
                                />
                                {movForm.movement_type !== "ajuste" && (
                                    <p className="text-xs text-zinc-600 mt-1">
                                        Nuevo stock: <span className="text-zinc-400 font-mono">
                                            {movForm.movement_type === "entrada"
                                                ? fmt(selectedProduct.stock_quantity + (movForm.quantity || 0))
                                                : fmt(Math.max(0, selectedProduct.stock_quantity - (movForm.quantity || 0)))}
                                        </span>
                                    </p>
                                )}
                            </div>
                            <div>
                                <label className="block text-xs text-zinc-400 mb-1.5 font-medium">Referencia (nº albarán, factura…)</label>
                                <input
                                    type="text" value={movForm.reference}
                                    onChange={e => setMovForm(f => ({ ...f, reference: e.target.value }))}
                                    className="w-full bg-[#18181b] border border-[#3f3f46] text-white text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-indigo-500 transition-colors"
                                    placeholder="ALB-2026-001"
                                />
                            </div>
                            <div>
                                <label className="block text-xs text-zinc-400 mb-1.5 font-medium">Notas</label>
                                <textarea
                                    value={movForm.notes} rows={2}
                                    onChange={e => setMovForm(f => ({ ...f, notes: e.target.value }))}
                                    className="w-full bg-[#18181b] border border-[#3f3f46] text-white text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-indigo-500 transition-colors resize-none"
                                    placeholder="Motivo del ajuste, devolución, etc."
                                />
                            </div>
                            <div className="flex gap-3 pt-2">
                                <button type="button" onClick={() => setShowModal(false)} className="flex-1 py-2.5 rounded-xl border border-[#3f3f46] text-zinc-400 text-sm hover:bg-white/5 transition-colors">
                                    Cancelar
                                </button>
                                <button type="submit" disabled={saving} className="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2">
                                    {saving && <Loader2 className="w-4 h-4 animate-spin" />}
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
