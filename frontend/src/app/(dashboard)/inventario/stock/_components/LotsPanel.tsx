"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, Plus, Pencil, Check, X, Layers } from "lucide-react";
import { useTranslations } from "next-intl";
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
    const t = useTranslations("inventario");
    if (!expiry) return <span className="text-xs text-muted-foreground italic">{t("lots.noExpiry")}</span>;
    const d = daysLeft(expiry);
    const cls =
        d === null ? "text-muted-foreground"
            : d < 0 ? "text-rose-400"
                : d <= 7 ? "text-amber-400"
                    : "text-foreground";
    const label =
        d === null ? "" : d < 0 ? ` (${t("lots.expiredAgo", { days: Math.abs(d) })})` : d === 0 ? ` (${t("lots.expiresToday")})` : ` (${d}d)`;
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
    const t = useTranslations("inventario");
    const tc = useTranslations("common");
    const [lots, setLots] = useState<ProductLot[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [showAdd, setShowAdd] = useState(false);
    const [form, setForm] = useState(emptyForm);
    const [editId, setEditId] = useState<string | null>(null);
    const [editForm, setEditForm] = useState({ lot_number: "", expiry_date: "", cost_price: "" });

    const load = useCallback(async () => {
        setLoading(true);
        try {
            setLots(await lotsApi.listForProduct(productId));
            setError(null);
        } catch (e: any) {
            setError(e?.message || t("lots.loadError"));
        }
        setLoading(false);
    }, [productId, t]);

    useEffect(() => { load();   }, [load]);

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
            setError(e?.message || t("lots.createError"));
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
            setError(e?.message || t("lots.updateError"));
        }
        setSaving(false);
    };

    return (
        <div className="rounded-lg border border-border bg-card p-4 space-y-3">
            <div className="flex items-center justify-between">
                <h4 className="flex items-center gap-2 text-sm font-medium text-foreground">
                    <Layers className="w-4 h-4 text-muted-foreground" /> {t("lots.title")}
                    <span className="text-xs font-normal text-muted-foreground">{t("lots.fefoNote")}</span>
                </h4>
                <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => setShowAdd(s => !s)}>
                    <Plus className="mr-1 w-3 h-3" /> {t("lots.addLot")}
                </Button>
            </div>

            {error && <p className="text-xs text-rose-400">{error}</p>}

            {showAdd && (
                <form onSubmit={handleAdd} className="grid grid-cols-2 sm:grid-cols-4 gap-2 items-end rounded-md border border-border/60 p-3">
                    <div>
                        <Label className="text-xs">{t("lots.lotNumber")}</Label>
                        <Input className="mt-1 h-8" value={form.lot_number} required
                            onChange={e => setForm(f => ({ ...f, lot_number: e.target.value }))} placeholder="L-2026-001" />
                    </div>
                    <div>
                        <Label className="text-xs">{t("lots.quantity")}</Label>
                        <Input className="mt-1 h-8" type="number" min={1} value={form.quantity}
                            onChange={e => setForm(f => ({ ...f, quantity: parseInt(e.target.value) || 0 }))} />
                    </div>
                    <div>
                        <Label className="text-xs">{t("lots.expiry")}</Label>
                        <Input className="mt-1 h-8" type="date" value={form.expiry_date}
                            onChange={e => setForm(f => ({ ...f, expiry_date: e.target.value }))} />
                    </div>
                    <div>
                        <Label className="text-xs">{t("lots.costPerUnit")}</Label>
                        <Input className="mt-1 h-8" type="number" step="0.01" min={0} value={form.cost_price}
                            onChange={e => setForm(f => ({ ...f, cost_price: e.target.value }))} placeholder={t("lots.optional")} />
                    </div>
                    <div className="col-span-2 sm:col-span-4 flex justify-end gap-2">
                        <Button type="button" variant="ghost" size="sm" onClick={() => { setShowAdd(false); setForm(emptyForm); }}>{tc("cancel")}</Button>
                        <Button type="submit" size="sm" disabled={saving}>
                            {saving && <Loader2 className="mr-2 w-3 h-3 animate-spin" />} {t("lots.saveLot")}
                        </Button>
                    </div>
                </form>
            )}

            {loading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
                    <Loader2 className="w-4 h-4 animate-spin" /> {t("lots.loadingLots")}
                </div>
            ) : lots.length === 0 ? (
                <p className="text-xs text-muted-foreground py-2">
                    {t("lots.empty")}
                </p>
            ) : (
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="text-xs text-muted-foreground border-b border-border">
                                <th className="text-left font-medium py-1.5">{t("lots.colLot")}</th>
                                <th className="text-left font-medium py-1.5">{t("lots.colExpiry")}</th>
                                <th className="text-right font-medium py-1.5">{t("lots.colQuantity")}</th>
                                <th className="text-right font-medium py-1.5">{t("lots.colCostPerUnit")}</th>
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
                                                <Button variant="ghost" size="icon" className="h-6 w-6" disabled={saving} onClick={() => saveEdit(lot.id)} title={tc("save")} aria-label={tc("save")}>
                                                    <Check className="w-3.5 h-3.5 text-emerald-400" aria-hidden="true" />
                                                </Button>
                                                <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => setEditId(null)} title={tc("cancel")} aria-label={tc("cancel")}>
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
                                                <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => startEdit(lot)} title={t("lots.editLot")} aria-label={t("lots.editLot")}>
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
