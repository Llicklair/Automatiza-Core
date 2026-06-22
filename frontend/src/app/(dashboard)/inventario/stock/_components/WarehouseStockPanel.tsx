"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, Warehouse as WarehouseIcon, ArrowLeftRight } from "lucide-react";
import { useTranslations } from "next-intl";
import { warehouses as whApi, type Warehouse, type WarehouseStock } from "@/lib/api/warehouses";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const fmt = (n: number) => n.toLocaleString("es-ES");

interface Props {
    productId: string;
    /** Se llama tras una transferencia, por si el padre quiere refrescar. */
    onChanged?: () => void;
}

export function WarehouseStockPanel({ productId, onChanged }: Props) {
    const t = useTranslations("inventario");
    const [stock, setStock] = useState<WarehouseStock[]>([]);
    const [whs, setWhs] = useState<Warehouse[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [showForm, setShowForm] = useState(false);
    const [from, setFrom] = useState("");
    const [to, setTo] = useState("");
    const [qty, setQty] = useState(1);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const [s, w] = await Promise.all([whApi.stockByProduct(productId), whApi.list()]);
            setStock(s);
            setWhs(w.filter(x => x.is_active));
            setError(null);
        } catch (e: any) {
            setError(e?.message || t("warehouseStock.loadError"));
        }
        setLoading(false);
    }, [productId, t]);

    useEffect(() => { load();   }, [load]);

    const doTransfer = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!from || !to || from === to || qty <= 0) {
            setError(t("warehouseStock.transferValidation"));
            return;
        }
        setSaving(true);
        try {
            await whApi.transfer({ product_id: productId, from_warehouse_id: from, to_warehouse_id: to, quantity: qty });
            setShowForm(false); setFrom(""); setTo(""); setQty(1);
            await load();
            onChanged?.();
        } catch (e: any) {
            setError(e?.message || t("warehouseStock.transferError"));
        }
        setSaving(false);
    };

    const canTransfer = whs.length >= 2;

    return (
        <div className="rounded-lg border border-border bg-card p-4 space-y-3">
            <div className="flex items-center justify-between">
                <h4 className="flex items-center gap-2 text-sm font-medium text-foreground">
                    <WarehouseIcon className="w-4 h-4 text-muted-foreground" /> {t("warehouseStock.title")}
                </h4>
                {canTransfer && (
                    <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => setShowForm(s => !s)}>
                        <ArrowLeftRight className="mr-1 w-3 h-3" /> {t("warehouseStock.transfer")}
                    </Button>
                )}
            </div>

            {error && <p className="text-xs text-rose-400">{error}</p>}

            {showForm && (
                <form onSubmit={doTransfer} className="grid grid-cols-2 sm:grid-cols-4 gap-2 items-end rounded-md border border-border/60 p-3">
                    <div>
                        <Label className="text-xs">{t("warehouseStock.from")}</Label>
                        <select value={from} onChange={e => setFrom(e.target.value)}
                            className="mt-1 w-full h-8 bg-background border border-border text-foreground text-sm rounded-md px-2">
                            <option value="">—</option>
                            {whs.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
                        </select>
                    </div>
                    <div>
                        <Label className="text-xs">{t("warehouseStock.to")}</Label>
                        <select value={to} onChange={e => setTo(e.target.value)}
                            className="mt-1 w-full h-8 bg-background border border-border text-foreground text-sm rounded-md px-2">
                            <option value="">—</option>
                            {whs.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
                        </select>
                    </div>
                    <div>
                        <Label className="text-xs">{t("warehouseStock.quantity")}</Label>
                        <Input className="mt-1 h-8" type="number" min={1} value={qty}
                            onChange={e => setQty(parseInt(e.target.value) || 0)} />
                    </div>
                    <div className="flex justify-end">
                        <Button type="submit" size="sm" disabled={saving} className="h-8">
                            {saving && <Loader2 className="mr-2 w-3 h-3 animate-spin" />} {t("warehouseStock.transfer")}
                        </Button>
                    </div>
                </form>
            )}

            {loading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
                    <Loader2 className="w-4 h-4 animate-spin" /> {t("warehouseStock.loading")}
                </div>
            ) : (
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="text-xs text-muted-foreground border-b border-border">
                                <th className="text-left font-medium py-1.5">{t("warehouseStock.colWarehouse")}</th>
                                <th className="text-right font-medium py-1.5">{t("warehouseStock.colQuantity")}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {stock.map(s => (
                                <tr key={s.warehouse_id} className="border-b border-border/40">
                                    <td className="py-1.5 text-foreground">
                                        {s.warehouse_name}
                                        {s.is_default && <span className="ml-2 text-[10px] text-muted-foreground">{t("warehouseStock.defaultTag")}</span>}
                                    </td>
                                    <td className="py-1.5 text-right font-mono text-foreground">{fmt(s.quantity)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    {!canTransfer && (
                        <p className="text-xs text-muted-foreground mt-2">
                            {t.rich("warehouseStock.transferHint", { path: (chunks) => <span className="text-foreground">{chunks}</span> })}
                        </p>
                    )}
                </div>
            )}
        </div>
    );
}
