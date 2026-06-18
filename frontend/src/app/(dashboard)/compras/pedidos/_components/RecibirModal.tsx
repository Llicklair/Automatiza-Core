"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Loader2 } from "lucide-react";
import { api, type PurchaseOrder } from "@/lib/api";
import { warehouses as whApi, type Warehouse } from "@/lib/api/warehouses";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";

interface RowState { quantity: number; lot_number: string; expiry_date: string; }

interface Props {
    order: PurchaseOrder | null;
    onClose: () => void;
    onReceived: () => void;
}

export function RecibirModal({ order, onClose, onReceived }: Props) {
    const t = useTranslations("compras.pedidos.receiveModal");
    const [whs, setWhs] = useState<Warehouse[]>([]);
    const [warehouseId, setWarehouseId] = useState("");
    const [rows, setRows] = useState<Record<string, RowState>>({});
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!order) return;
        whApi.list().then(list => {
            const active = list.filter(w => w.is_active);
            setWhs(active);
            setWarehouseId((active.find(w => w.is_default) || active[0])?.id || "");
        }).catch(() => setWhs([]));
        const init: Record<string, RowState> = {};
        for (const l of order.lines || []) {
            if (!l.id) continue;
            const remaining = Number(l.quantity || 0) - Number(l.received_quantity || 0);
            init[l.id] = { quantity: Math.max(0, remaining), lot_number: "", expiry_date: "" };
        }
        setRows(init);
        setError(null);
    }, [order]);

    if (!order) return null;

    const submit = async (e: React.FormEvent) => {
        e.preventDefault();
        const lines = (order.lines || [])
            .filter(l => l.id && (rows[l.id]?.quantity || 0) > 0)
            .map(l => ({
                line_id: l.id as string,
                quantity: rows[l.id!].quantity,
                lot_number: rows[l.id!].lot_number.trim() || null,
                expiry_date: rows[l.id!].expiry_date || null,
            }));
        if (lines.length === 0) { setError(t("errorNoQuantity")); return; }
        setSaving(true);
        try {
            await api.erp.purchaseOrders.receive(order.id, { warehouse_id: warehouseId || null, lines });
            onReceived();
            onClose();
        } catch (e: any) {
            setError(e?.message || t("errorGeneric"));
        }
        setSaving(false);
    };

    return (
        <Dialog open={!!order} onOpenChange={o => { if (!o) onClose(); }}>
            <DialogContent className="sm:max-w-2xl">
                <DialogHeader>
                    <DialogTitle>{t("title")}</DialogTitle>
                    <DialogDescription>
                        {t("subtitle", { number: order.order_number || order.id.slice(0, 8), supplier: order.supplier?.name || "" })}
                    </DialogDescription>
                </DialogHeader>
                <form onSubmit={submit} className="space-y-4">
                    <div>
                        <Label className="text-xs">{t("warehouse")}</Label>
                        <select value={warehouseId} onChange={e => setWarehouseId(e.target.value)}
                            className="mt-1.5 w-full h-9 bg-background border border-border text-foreground text-sm rounded-md px-3">
                            {whs.map(w => <option key={w.id} value={w.id}>{w.name}{w.is_default ? t("defaultSuffix") : ""}</option>)}
                        </select>
                    </div>

                    {error && <p className="text-xs text-rose-400">{error}</p>}

                    <div className="space-y-3 max-h-[45vh] overflow-y-auto pr-1">
                        {(order.lines || []).map(line => {
                            if (!line.id) return null;
                            const remaining = Number(line.quantity || 0) - Number(line.received_quantity || 0);
                            const row = rows[line.id] || { quantity: 0, lot_number: "", expiry_date: "" };
                            return (
                                <div key={line.id} className="rounded-md border border-border/60 p-3">
                                    <div className="flex items-center justify-between gap-2">
                                        <span className="text-sm text-foreground">{line.description}</span>
                                        <span className="text-xs text-muted-foreground">
                                            {t("ordered", { quantity: Number(line.quantity), remaining })}
                                        </span>
                                    </div>
                                    <div className="grid grid-cols-3 gap-2 mt-2">
                                        <div>
                                            <Label className="text-xs">{t("receive")}</Label>
                                            <Input className="mt-1 h-8" type="number" min={0} max={remaining}
                                                value={row.quantity}
                                                onChange={e => setRows(r => ({ ...r, [line.id!]: { ...row, quantity: Math.min(remaining, parseInt(e.target.value) || 0) } }))} />
                                        </div>
                                        <div>
                                            <Label className="text-xs">{t("lotNumber")}</Label>
                                            <Input className="mt-1 h-8" value={row.lot_number}
                                                onChange={e => setRows(r => ({ ...r, [line.id!]: { ...row, lot_number: e.target.value } }))} />
                                        </div>
                                        <div>
                                            <Label className="text-xs">{t("expiry")}</Label>
                                            <Input className="mt-1 h-8" type="date" value={row.expiry_date}
                                                onChange={e => setRows(r => ({ ...r, [line.id!]: { ...row, expiry_date: e.target.value } }))} />
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>

                    <DialogFooter>
                        <Button type="button" variant="outline" onClick={onClose}>{t("cancel")}</Button>
                        <Button type="submit" disabled={saving}>
                            {saving && <Loader2 className="mr-2 w-4 h-4 animate-spin" />} {t("confirm")}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
