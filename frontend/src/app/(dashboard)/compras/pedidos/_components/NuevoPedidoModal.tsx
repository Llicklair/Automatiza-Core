"use client";

import { type Client, type Product, type PurchaseOrderLine } from "@/lib/api";
import { Plus, X, Loader2 } from "lucide-react";
import { type PedidoForm } from "../_hooks/usePedidosCompra";

const fmt = (n: number) => n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });

interface Props {
    open: boolean;
    onClose: () => void;
    form: PedidoForm;
    setForm: React.Dispatch<React.SetStateAction<PedidoForm>>;
    suppliers: Client[];
    products: Product[];
    saving: boolean;
    orderTotal: number;
    lineTotal: (line: PurchaseOrderLine) => number;
    setLine: (i: number, field: keyof PurchaseOrderLine, value: any) => void;
    onSubmit: (e: React.FormEvent) => void;
}

const EMPTY_LINE: PurchaseOrderLine = { description: "", quantity: 1, unit_price: 0, tax_percentage: 21 };

export function NuevoPedidoModal({ open, onClose, form, setForm, suppliers, products, saving, orderTotal, lineTotal, setLine, onSubmit }: Props) {
    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 backdrop-blur-sm pt-16 pb-8 overflow-y-auto">
            <div className="bg-card border border-border rounded-2xl p-8 w-full max-w-2xl shadow-2xl">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-lg font-bold text-foreground">Nuevo pedido de compra</h2>
                    <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors"><X className="w-5 h-5" /></button>
                </div>
                <form onSubmit={onSubmit} className="space-y-6">
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
                                        <button type="button" onClick={() => setForm(f => ({ ...f, lines: f.lines.filter((_, idx) => idx !== i) }))}
                                            disabled={form.lines.length === 1}
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
                        <button type="button" onClick={onClose}
                            className="flex-1 py-2.5 rounded-xl border border-border text-muted-foreground text-sm hover:bg-accent/50 transition-colors">
                            Cancelar
                        </button>
                        <button type="submit" disabled={saving}
                            className="flex-1 py-2.5 rounded-xl bg-primary hover:bg-primary text-foreground text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2">
                            {saving && <Loader2 className="w-4 h-4 animate-spin" />} Crear pedido
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
