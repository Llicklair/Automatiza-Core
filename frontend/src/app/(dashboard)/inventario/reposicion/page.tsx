"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw, Loader2, ShoppingCart, AlertTriangle, CheckCircle2 } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { reorder as reorderApi, type ReorderSuggestion, type GeneratePosResult } from "@/lib/api/reorder";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";

const fmt = (n: number) => n.toLocaleString("es-ES");

export default function ReposicionPage() {
    const t = useTranslations("inventario");
    const tc = useTranslations("common");
    const [items, setItems] = useState<ReorderSuggestion[]>([]);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<GeneratePosResult | null>(null);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            setItems(await reorderApi.suggestions());
            setError(null);
        } catch (e: any) {
            setError(e?.message || t("reorder.loadError"));
        }
        setLoading(false);
    }, [t]);

    useEffect(() => { load(); }, [load]);

    const generate = async () => {
        setGenerating(true);
        setResult(null);
        try {
            const r = await reorderApi.generatePurchaseOrders();
            setResult(r);
            await load();
        } catch (e: any) {
            setError(e?.message || t("reorder.generateError"));
        }
        setGenerating(false);
    };

    const withSupplier = items.filter(i => i.supplier_id).length;

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title={t("reorder.title")}
                description={t("reorder.description")}
                icon={ShoppingCart}
                actions={
                    <div className="flex items-center gap-2">
                        <Button variant="outline" onClick={load} disabled={loading}>
                            <RefreshCw className="mr-2 h-4 w-4" /> {t("reorder.refresh")}
                        </Button>
                        <Button onClick={generate} disabled={generating || withSupplier === 0}>
                            {generating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ShoppingCart className="mr-2 h-4 w-4" />}
                            {t("reorder.generateOrders")}
                        </Button>
                    </div>
                }
            />

            {error && <p className="text-sm text-rose-400">{error}</p>}

            {result && (
                <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-4 text-sm space-y-1">
                    <p className="flex items-center gap-2 text-emerald-300">
                        <CheckCircle2 className="w-4 h-4" />
                        {t("reorder.ordersCreated", { count: result.created.length })}
                    </p>
                    {result.created.length > 0 && (
                        <Link href="/compras/pedidos" className="text-xs text-emerald-300 underline underline-offset-2">
                            {t("reorder.viewOrders")}
                        </Link>
                    )}
                    {result.skipped_no_supplier.length > 0 && (
                        <p className="flex items-center gap-2 text-amber-300">
                            <AlertTriangle className="w-4 h-4" />
                            {t("reorder.skippedNoSupplier", { count: result.skipped_no_supplier.length, names: result.skipped_no_supplier.join(", ") })}
                        </p>
                    )}
                </div>
            )}

            {loading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="w-4 h-4 animate-spin" /> {tc("loading")}</div>
            ) : items.length === 0 ? (
                <div className="rounded-lg border border-border bg-card p-8 text-center text-sm text-muted-foreground">
                    {t("reorder.empty")} 👍
                </div>
            ) : (
                <div className="rounded-lg border border-border bg-card overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="text-xs text-muted-foreground border-b border-border">
                                <th className="text-left font-medium p-3">{t("reorder.product")}</th>
                                <th className="text-right font-medium p-3">{t("reorder.stock")}</th>
                                <th className="text-right font-medium p-3" title={t("reorder.reorderPointHint")}>{t("reorder.reorderPoint")}</th>
                                <th className="text-right font-medium p-3">{t("reorder.suggested")}</th>
                                <th className="text-left font-medium p-3">{t("reorder.supplier")}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {items.map(it => (
                                <tr key={it.product_id} className="border-b border-border/40">
                                    <td className="p-3 text-foreground">
                                        {it.name}
                                        {it.sku && <span className="ml-2 text-xs text-muted-foreground font-mono">{it.sku}</span>}
                                    </td>
                                    <td className="p-3 text-right font-mono text-rose-400">{fmt(it.current_stock)}</td>
                                    <td className="p-3 text-right font-mono text-muted-foreground">{fmt(it.reorder_point)}</td>
                                    <td className="p-3 text-right font-mono text-foreground">+{fmt(it.suggested_qty)}</td>
                                    <td className="p-3">
                                        {it.supplier_name
                                            ? <span className="text-foreground">{it.supplier_name}</span>
                                            : <span className="text-amber-400 text-xs">{t("reorder.noSupplier")}</span>}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
