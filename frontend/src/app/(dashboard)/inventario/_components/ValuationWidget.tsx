"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Coins, Loader2, Package, Tags } from "lucide-react";
import { api, type StockValuation } from "@/lib/api";
import { KpiCard } from "@/components/shared/KpiCard";

const fmtEUR = (n: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(n);
const fmtInt = (n: number) => n.toLocaleString("es-ES");

export function ValuationWidget() {
    const [data, setData] = useState<StockValuation | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        api.erp.stock.valuation()
            .then(setData)
            .catch((e: any) => setError(e?.message || "Error cargando valoración"))
            .finally(() => setLoading(false));
    }, []);

    if (loading) {
        return (
            <div className="bg-card border border-border rounded-2xl p-6 flex items-center justify-center text-muted-foreground gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-sm">Calculando valoración…</span>
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="bg-card border border-destructive/30 rounded-2xl p-4 text-sm text-destructive">
                {error || "No se pudo cargar la valoración"}
            </div>
        );
    }

    const topCategories = data.by_category.slice(0, 5);

    return (
        <div className="space-y-4">
            <div className="flex items-baseline justify-between">
                <h2 className="text-lg font-semibold text-foreground">Valoración de inventario</h2>
                <span className="text-xs text-muted-foreground">
                    Solo productos activos · coste × stock
                </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <KpiCard
                    title="Valor total"
                    value={fmtEUR(data.total_value)}
                    icon={Coins}
                />
                <KpiCard
                    title="Unidades en stock"
                    value={fmtInt(data.total_units)}
                    icon={Package}
                />
                <KpiCard
                    title="Productos activos"
                    value={fmtInt(data.product_count)}
                    icon={Tags}
                />
            </div>

            {data.missing_cost_price_count > 0 && (
                <div className="flex items-start gap-2 bg-amber-500/5 border border-amber-500/20 rounded-xl px-4 py-3">
                    <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                    <div className="text-xs leading-relaxed">
                        <p className="text-foreground font-medium">
                            {fmtInt(data.missing_cost_price_count)} producto(s) sin precio de coste
                        </p>
                        <p className="text-muted-foreground">
                            La valoración total es parcial. Añade <em>coste</em> a esos productos para incluirlos.
                        </p>
                    </div>
                </div>
            )}

            {topCategories.length > 0 ? (
                <div className="bg-card border border-border rounded-2xl overflow-hidden">
                    <div className="px-4 py-2.5 border-b border-border bg-muted/40">
                        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                            Top categorías por valor
                        </p>
                    </div>
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="text-xs text-muted-foreground border-b border-border">
                                <th className="text-left font-medium px-4 py-2">Categoría</th>
                                <th className="text-right font-medium px-4 py-2">Unidades</th>
                                <th className="text-right font-medium px-4 py-2">Productos</th>
                                <th className="text-right font-medium px-4 py-2">Valor</th>
                            </tr>
                        </thead>
                        <tbody>
                            {topCategories.map((c) => (
                                <tr key={c.category ?? "__none__"} className="border-b border-border last:border-0">
                                    <td className="px-4 py-2.5 text-foreground">
                                        {c.category || <span className="italic text-muted-foreground">Sin categoría</span>}
                                    </td>
                                    <td className="px-4 py-2.5 text-right font-mono tabular-nums text-foreground">
                                        {fmtInt(c.units)}
                                    </td>
                                    <td className="px-4 py-2.5 text-right font-mono tabular-nums text-muted-foreground">
                                        {fmtInt(c.product_count)}
                                    </td>
                                    <td className="px-4 py-2.5 text-right font-mono tabular-nums font-semibold text-foreground">
                                        {fmtEUR(c.value)}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ) : (
                <div className="bg-card border border-border rounded-2xl px-4 py-6 text-center text-sm text-muted-foreground">
                    Sin productos activos para valorar.
                </div>
            )}
        </div>
    );
}
