"use client";

import { useEffect, useState } from "react";
import { BarChart3, Loader2, Package, TrendingUp, Skull, Coins } from "lucide-react";
import { inventoryAnalytics as invApi, type InventoryAnalytics } from "@/lib/api/inventory_analytics";
import { PageHeader } from "@/components/shared/PageHeader";
import { KpiCard } from "@/components/shared/KpiCard";

const eur = (n: number) => n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });
const num = (n: number) => n.toLocaleString("es-ES");
const DEAD_RANGES = [30, 60, 90, 180];

export default function InventarioAnaliticaPage() {
    const [data, setData] = useState<InventoryAnalytics | null>(null);
    const [loading, setLoading] = useState(true);
    const [deadDays, setDeadDays] = useState(90);

    useEffect(() => {
        let active = true;
        setLoading(true);
        invApi.overview(deadDays, 30)
            .then(d => { if (active) setData(d); })
            .catch(() => { if (active) setData(null); })
            .finally(() => { if (active) setLoading(false); });
        return () => { active = false; };
    }, [deadDays]);

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Analítica de inventario"
                description="Valoración del stock, productos que no rotan (stock muerto) y los más vendidos."
                icon={BarChart3}
            />

            {loading || !data ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="w-4 h-4 animate-spin" /> Cargando…</div>
            ) : (
                <>
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                        <KpiCard title="Valoración a coste" value={eur(data.valuation.value_cost)} icon={Coins} />
                        <KpiCard title="Valoración a PVP" value={eur(data.valuation.value_retail)} icon={Package} />
                        <KpiCard title="Margen potencial" value={eur(data.valuation.potential_margin)} icon={TrendingUp} />
                        <KpiCard
                            title="Stock muerto"
                            value={`${data.dead_count} · ${eur(data.dead_value_cost)}`}
                            icon={Skull}
                            className={data.dead_count > 0 ? "border-rose-500/20" : ""}
                        />
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        {/* Más vendidos */}
                        <div className="rounded-lg border border-border bg-card p-4">
                            <h3 className="flex items-center gap-2 text-sm font-medium text-foreground mb-3">
                                <TrendingUp className="w-4 h-4 text-emerald-400" /> Más vendidos (últimos {data.top_days} días)
                            </h3>
                            {data.top_movers.length === 0 ? (
                                <p className="text-xs text-muted-foreground">Sin ventas en el periodo.</p>
                            ) : (
                                <table className="w-full text-sm">
                                    <thead><tr className="text-xs text-muted-foreground border-b border-border">
                                        <th className="text-left font-medium py-1.5">Producto</th>
                                        <th className="text-right font-medium py-1.5">Uds vendidas</th>
                                    </tr></thead>
                                    <tbody>
                                        {data.top_movers.map(t => (
                                            <tr key={t.product_id} className="border-b border-border/40">
                                                <td className="py-1.5 text-foreground">{t.name}</td>
                                                <td className="py-1.5 text-right font-mono text-foreground">{num(t.sold)}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </div>

                        {/* Stock muerto */}
                        <div className="rounded-lg border border-border bg-card p-4">
                            <div className="flex items-center justify-between mb-3">
                                <h3 className="flex items-center gap-2 text-sm font-medium text-foreground">
                                    <Skull className="w-4 h-4 text-rose-400" /> Stock muerto
                                </h3>
                                <div className="flex items-center gap-1">
                                    {DEAD_RANGES.map(r => (
                                        <button key={r} type="button" onClick={() => setDeadDays(r)}
                                            className={`text-xs px-2 py-1 rounded-md border transition-colors ${deadDays === r ? "bg-primary/15 border-primary/40 text-foreground" : "border-border text-muted-foreground hover:text-foreground"}`}>
                                            {r}d
                                        </button>
                                    ))}
                                </div>
                            </div>
                            {data.dead_stock.length === 0 ? (
                                <p className="text-xs text-muted-foreground">Nada parado sin vender en {deadDays} días. 👍</p>
                            ) : (
                                <table className="w-full text-sm">
                                    <thead><tr className="text-xs text-muted-foreground border-b border-border">
                                        <th className="text-left font-medium py-1.5">Producto</th>
                                        <th className="text-right font-medium py-1.5">Stock</th>
                                        <th className="text-right font-medium py-1.5">Sin vender</th>
                                        <th className="text-right font-medium py-1.5">Valor</th>
                                    </tr></thead>
                                    <tbody>
                                        {data.dead_stock.map(d => (
                                            <tr key={d.product_id} className="border-b border-border/40">
                                                <td className="py-1.5 text-foreground">{d.name}</td>
                                                <td className="py-1.5 text-right font-mono text-foreground">{num(d.stock)}</td>
                                                <td className="py-1.5 text-right text-muted-foreground">
                                                    {d.days_since_sale === null ? "nunca" : `${d.days_since_sale}d`}
                                                </td>
                                                <td className="py-1.5 text-right font-mono text-foreground">{eur(d.value_cost)}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
