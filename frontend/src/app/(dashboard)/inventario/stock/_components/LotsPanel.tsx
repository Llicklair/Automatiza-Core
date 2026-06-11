"use client";

import { useEffect, useState } from "react";
import { Loader2, Plus, Pencil, Check, X, Layers } from "lucide-react";
import { lots as lotsApi, type ProductLot } from "@/lib/api/inventory_lots";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const fmt = (n: number) => n.toLocaleString("es-ES");

/** Días hasta caducar (negativo si ya caducó), o null si el lote no tiene caducidad. */
function daysLeft(expiry: string | null): number | null {
    if (!expiry) return null;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const exp = new Date(expiry + "T00:00:00");
    return Math.round((exp.getTime() - today.getTime()) / 86_400_000);
}

function ExpiryBadge({ expiry }: { expiry: string | null }) {
    if (!expiry) return <span className="text-xs text-muted-foreground italic">sin caducidad</span>;
    const d = daysLeft(expiry);
    const cls =
        d === null ? "text-muted-foreground"
            : d < 0 ? "text-rose-400"
                : d <= 7 ? "text-amber-400"
                    : "text-foreground";
    const label =
        d === null ? "" : d < 0 ? ` (caducado hace ${Math.abs(d)}d)` : d === 0 ? " (caduca hoy)" : ` (${d}d)`;
    return (
        <span className={`text-sm font-mono ${cls}`}>
            {expiry}
            <span className="text-xs">{label}</span>
        </span>
    );
}

interface LotsPanelProps {
    productId: string;
    /** Notifica al padre que el stock agregado cambió (alta de lote), para refrescar. */
    onStockChanged?: () => void;
}

const emptyForm = { lot_number: "", quantity: 1, expiry_date: "", cost_price: "" };

export function LotsPanel({ productId, onStockChanged }: LotsPanelProps) {
    const [lots, setLots] = useState<ProductLot[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [showAdd, setShowAdd] = useState(false);
    const [form, setForm] = useState(emptyForm);
    const [editId, setEditId] = useState<string | null>(null);
    const [editForm, setEditForm] = useState({ lot_number: "", expiry_date: "", cost_price: "" });

    const load = async () => {
        setLoading(true);
        try {
            setLots(await lotsApi.listForProduct(productId));
            setError(null);
        } catch (e: any) {
            setError(e?.message || "No se pudieron cargar los lotes");
        }
        setLoading(false);
    };

    useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [productId]);

    const handleAdd = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.lot_number.trim() || form.quantity <= 0) return;
        setSaving(true);
        try {
            await lotsApi.create(productId, {
                lot_number: form.lot_number.trim(),
                quantity: form.quantity,
                expiry_date: form.expiry_date || null,
                cost_price: form.cost_price === "" ? null : Number(form.cost_price),
            });
            setForm(emptyForm);
            setShowAdd(false);
            await load();
            onStockChanged?.();
        } catch (e: any) {
            setError(e?.message || "No se pudo crear el lote");
        }
        setSaving(false);
    };

    const startEdit = (lot: ProductLot) => {
        setEditId(lot.id);
        setEditForm({
            lot_number: lot.lot_number,
            expiry_date: lot.expiry_date || "",
            cost_price: lot.cost_price === null ? "" : String(lot.cost_price),
        });
    };

    const saveEdit = async (lotId: string) => {
        setSaving(true);
        try {
            await lotsApi.update(productId, lotId, {
                lot_number: editForm.lot_number.trim(),
                expiry_date: editForm.expiry_date || null,
                cost_price: editForm.cost_price === "" ? null : Number(editForm.cost_price),
            });
            setEditId(null);
            await load();
        } catch (e: any) {
            setError(e?.message || "No se pudo actualizar el lote");
        }
        setSaving(false);
    };

    return (
        <div className="rounded-lg border border-border bg-card p-4 space-y-3">
            <div className="flex items-center justify-between">
                <h4 className="flex items-center gap-2 text-sm font-medium text-foreground">
                    <Layers className="w-4 h-4 text-muted-foreground" /> Lotes y caducidad
                    <span className="text-xs font-normal text-muted-foreground">· al vender se gasta antes lo que antes caduca</span>
                </h4>
                <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => setShowAdd(s => !s)}>
                    <Plus className="mr-1 w-3 h-3" /> Añadir lote
                </Button>
            </div>

            {error && <p className="text-xs text-rose-400">{error}</p>}

            {showAdd && (
                <form onSubmit={handleAdd} className="grid grid-cols-2 sm:grid-cols-4 gap-2 items-end rounded-md border border-border/60 p-3">
                    <div>
                        <Label className="text-xs">Nº de lote</Label>
                        <Input className="mt-1 h-8" value={form.lot_number} required
                            onChange={e => setForm(f => ({ ...f, lot_number: e.target.value }))} placeholder="L-2026-001" />
                    </div>
                    <div>
                        <Label className="text-xs">Cantidad</Label>
                        <Input className="mt-1 h-8" type="number" min={1} value={form.quantity}
                            onChange={e => setForm(f => ({ ...f, quantity: parseInt(e.target.value) || 0 }))} />
                    </div>
                    <div>
                        <Label className="text-xs">Caducidad</Label>
                        <Input className="mt-1 h-8" type="date" value={form.expiry_date}
                            onChange={e => setForm(f => ({ ...f, expiry_date: e.target.value }))} />
                    </div>
                    <div>
                        <Label className="text-xs">Coste/ud (€)</Label>
                        <Input className="mt-1 h-8" type="number" step="0.01" min={0} value={form.cost_price}
                            onChange={e => setForm(f => ({ ...f, cost_price: e.target.value }))} placeholder="opcional" />
                    </div>
                    <div className="col-span-2 sm:col-span-4 flex justify-end gap-2">
                        <Button type="button" variant="ghost" size="sm" onClick={() => { setShowAdd(false); setForm(emptyForm); }}>Cancelar</Button>
                        <Button type="submit" size="sm" disabled={saving}>
                            {saving && <Loader2 className="mr-2 w-3 h-3 animate-spin" />} Guardar lote
                        </Button>
                    </div>
                </form>
            )}

            {loading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
                    <Loader2 className="w-4 h-4 animate-spin" /> Cargando lotes...
                </div>
            ) : lots.length === 0 ? (
                <p className="text-xs text-muted-foreground py-2">
                    Este producto no gestiona lotes. Añade uno para activar el control de caducidad y el descuento FEFO en las salidas.
                </p>
            ) : (
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="text-xs text-muted-foreground border-b border-border">
                                <th className="text-left font-medium py-1.5">Lote</th>
                                <th className="text-left font-medium py-1.5">Caducidad</th>
                                <th className="text-right font-medium py-1.5">Cantidad</th>
                                <th className="text-right font-medium py-1.5">Coste/ud</th>
                                <th className="text-right font-medium py-1.5"></th>
                            </tr>
                        </thead>
                        <tbody>
                            {lots.map(lot => (
                                <tr key={lot.id} className="border-b border-border/40">
                                    {editId === lot.id ? (
                                        <>
                                            <td className="py-1.5 pr-2">
                                                <Input className="h-7 text-xs" value={editForm.lot_number}
                                                    onChange={e => setEditForm(f => ({ ...f, lot_number: e.target.value }))} />
                                            </td>
                                            <td className="py-1.5 pr-2">
                                                <Input className="h-7 text-xs" type="date" value={editForm.expiry_date}
                                                    onChange={e => setEditForm(f => ({ ...f, expiry_date: e.target.value }))} />
                                            </td>
                                            <td className="py-1.5 text-right font-mono text-muted-foreground">{fmt(lot.quantity)}</td>
                                            <td className="py-1.5 pl-2">
                                                <Input className="h-7 text-xs" type="number" step="0.01" value={editForm.cost_price}
                                                    onChange={e => setEditForm(f => ({ ...f, cost_price: e.target.value }))} />
                                            </td>
                                            <td className="py-1.5 text-right whitespace-nowrap">
                                                <Button variant="ghost" size="icon" className="h-6 w-6" disabled={saving} onClick={() => saveEdit(lot.id)} title="Guardar" aria-label="Guardar">
                                                    <Check className="w-3.5 h-3.5 text-emerald-400" aria-hidden="true" />
                                                </Button>
                                                <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => setEditId(null)} title="Cancelar" aria-label="Cancelar">
                                                    <X className="w-3.5 h-3.5" aria-hidden="true" />
                                                </Button>
                                            </td>
                                        </>
                                    ) : (
                                        <>
                                            <td className="py-1.5 font-mono text-foreground">{lot.lot_number}</td>
                                            <td className="py-1.5"><ExpiryBadge expiry={lot.expiry_date} /></td>
                                            <td className="py-1.5 text-right font-mono text-foreground">{fmt(lot.quantity)}</td>
                                            <td className="py-1.5 text-right font-mono text-muted-foreground">
                                                {lot.cost_price === null ? "—" : `${lot.cost_price.toFixed(2)} €`}
                                            </td>
                                            <td className="py-1.5 text-right">
                                                <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => startEdit(lot)} title="Editar lote" aria-label="Editar lote">
                                                    <Pencil className="w-3 h-3" aria-hidden="true" />
                                                </Button>
                                            </td>
                                        </>
                                    )}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
