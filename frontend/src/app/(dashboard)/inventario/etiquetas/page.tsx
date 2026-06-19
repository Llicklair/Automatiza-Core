"use client";

import { useEffect, useState } from "react";
import { Tags, Search, Plus, Trash2, Loader2, Printer } from "lucide-react";
import { useTranslations } from "next-intl";
import { api, type Product } from "@/lib/api";
import { labels as labelsApi } from "@/lib/api/labels";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface Selected { product: Product; copies: number; }

export default function EtiquetasPage() {
    const t = useTranslations("inventario");
    const tc = useTranslations("common");
    const [query, setQuery] = useState("");
    const [results, setResults] = useState<Product[]>([]);
    const [selected, setSelected] = useState<Record<string, Selected>>({});
    const [showPrice, setShowPrice] = useState(true);
    const [searching, setSearching] = useState(false);
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let active = true;
        const t = setTimeout(async () => {
            setSearching(true);
            try {
                const data = await api.erp.products.list({ q: query || undefined, limit: 25, is_active: true });
                if (active) setResults(data);
            } catch { if (active) setResults([]); }
            if (active) setSearching(false);
        }, 300);
        return () => { active = false; clearTimeout(t); };
    }, [query]);

    const add = (p: Product) => setSelected(s => ({ ...s, [p.id]: { product: p, copies: s[p.id]?.copies || 1 } }));
    const setCopies = (id: string, n: number) => setSelected(s => ({ ...s, [id]: { ...s[id], copies: Math.max(1, n) } }));
    const remove = (id: string) => setSelected(s => { const c = { ...s }; delete c[id]; return c; });

    const list = Object.values(selected);
    const totalLabels = list.reduce((a, s) => a + s.copies, 0);

    const generate = async () => {
        if (list.length === 0) return;
        setGenerating(true); setError(null);
        try {
            const blob = await labelsApi.pdf(list.map(s => ({ product_id: s.product.id, copies: s.copies })), showPrice);
            const url = URL.createObjectURL(blob);
            window.open(url, "_blank");
            setTimeout(() => URL.revokeObjectURL(url), 60_000);
        } catch (e: any) {
            setError(e?.message || t("labels.generateError"));
        }
        setGenerating(false);
    };

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title={t("labels.title")}
                description={t("labels.description")}
                icon={Tags}
                actions={
                    <Button onClick={generate} disabled={generating || totalLabels === 0}>
                        {generating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Printer className="mr-2 h-4 w-4" />}
                        {t("labels.generate")} {totalLabels > 0 ? `(${totalLabels})` : ""}
                    </Button>
                }
            />

            {error && <p className="text-sm text-rose-400">{error}</p>}

            <div className="flex items-center gap-2">
                <input id="lbl-price" type="checkbox" checked={showPrice} onChange={e => setShowPrice(e.target.checked)} className="h-4 w-4 accent-primary" />
                <Label htmlFor="lbl-price" className="text-sm cursor-pointer">{t("labels.includePrice")}</Label>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Buscar productos */}
                <div className="rounded-lg border border-border bg-card p-4 space-y-3">
                    <div className="relative">
                        <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                        <Input value={query} onChange={e => setQuery(e.target.value)} placeholder={t("labels.searchPlaceholder")} className="pl-9" />
                    </div>
                    <div className="max-h-[55vh] overflow-y-auto divide-y divide-border/40">
                        {searching ? (
                            <div className="flex items-center gap-2 text-sm text-muted-foreground py-3"><Loader2 className="w-4 h-4 animate-spin" /> {t("labels.searching")}</div>
                        ) : results.length === 0 ? (
                            <p className="text-xs text-muted-foreground py-3">{tc("noResults")}</p>
                        ) : results.map(p => (
                            <div key={p.id} className="flex items-center justify-between gap-2 py-2">
                                <div className="min-w-0">
                                    <p className="text-sm text-foreground truncate">{p.name}</p>
                                    <p className="text-xs text-muted-foreground font-mono">{p.barcode || p.sku || t("labels.noCode")}</p>
                                </div>
                                <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => add(p)}>
                                    <Plus className="w-3 h-3 mr-1" /> {t("labels.add")}
                                </Button>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Selección a imprimir */}
                <div className="rounded-lg border border-border bg-card p-4 space-y-3">
                    <h3 className="text-sm font-medium text-foreground">{t("labels.toPrint", { count: totalLabels })}</h3>
                    {list.length === 0 ? (
                        <p className="text-xs text-muted-foreground py-3">{t("labels.emptySelection")}</p>
                    ) : (
                        <div className="space-y-2 max-h-[55vh] overflow-y-auto">
                            {list.map(({ product, copies }) => (
                                <div key={product.id} className="flex items-center gap-2">
                                    <span className="flex-1 text-sm text-foreground truncate">{product.name}</span>
                                    <Input type="number" min={1} value={copies}
                                        onChange={e => setCopies(product.id, parseInt(e.target.value) || 1)}
                                        className="h-8 w-20" />
                                    <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => remove(product.id)} aria-label={t("labels.removeProduct")}>
                                        <Trash2 className="w-3.5 h-3.5 text-muted-foreground" aria-hidden="true" />
                                    </Button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
