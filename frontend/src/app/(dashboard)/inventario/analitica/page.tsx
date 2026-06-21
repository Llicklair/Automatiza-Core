"use client";

import { useEffect, useState } from "react";
import { BarChart3, Loader2, Package, TrendingUp, Skull, Coins, PackageMinus, Boxes, AlertTriangle } from "lucide-react";
import { useTranslations } from "next-intl";
import { inventoryAnalytics as invApi, type InventoryAnalytics } from "@/lib/api/inventory_analytics";
import { PageHeader } from "@/components/shared/PageHeader";
import { KpiCard } from "@/components/shared/KpiCard";

const eur = (n: number) => n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });
const num = (n: number) => n.toLocaleString("es-ES");
const DEAD_RANGES = [30, 60, 90, 180];

const BAJA_REASONS = ["rotura", "merma", "robo", "caducado"] as const;

export default function InventarioAnaliticaPage() {
    const t = useTranslations("inventario");
    const reasonLabel = (reason: string) =>
        (BAJA_REASONS as readonly string[]).includes(reason)
            ? t(`analytics.reason.${reason}` as `analytics.reason.${(typeof BAJA_REASONS)[number]}`)
            : reason;
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
                title={t("analytics.title")}
                description={t("analytics.description")}
                icon={BarChart3}
            />

            {loading || !data ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="w-4 h-4 animate-spin" /> {t("analytics.loading")}</div>
            ) : (
                <>
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                        <KpiCard title={t("analytics.valuationCost")} value={eur(data.valuation.value_cost)} icon={Coins} />
                        <KpiCard title={t("analytics.valuationRetail")} value={eur(data.valuation.value_retail)} icon={Package} />
                        <KpiCard title={t("analytics.potentialMargin")} value={eur(data.valuation.potential_margin)} icon={TrendingUp} />
                        <KpiCard
                            title={t("analytics.deadStock")}
                            value={`${data.dead_count} · ${eur(data.dead_value_cost)}`}
                            icon={Skull}
                            className={data.dead_count > 0 ? "border-rose-500/20" : ""}
                        />
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        {/* Más vendidos */}
                        <div className="rounded-lg border border-border bg-card p-4">
                            <h3 className="flex items-center gap-2 text-sm font-medium text-foreground mb-3">
                                <TrendingUp className="w-4 h-4 text-emerald-400" /> {t("analytics.topMovers", { days: data.top_days })}
                            </h3>
                            {data.top_movers.length === 0 ? (
                                <p className="text-xs text-muted-foreground">{t("analytics.noSales")}</p>
                            ) : (
                                <table className="w-full text-sm">
                                    <thead><tr className="text-xs text-muted-foreground border-b border-border">
                                        <th className="text-left font-medium py-1.5">{t("analytics.product")}</th>
                                        <th className="text-right font-medium py-1.5">{t("analytics.unitsSold")}</th>
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
                                    <Skull className="w-4 h-4 text-rose-400" /> {t("analytics.deadStock")}
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
                                <p className="text-xs text-muted-foreground">{t("analytics.noDeadStock", { days: deadDays })} 👍</p>
                            ) : (
                                <table className="w-full text-sm">
                                    <thead><tr className="text-xs text-muted-foreground border-b border-border">
                                        <th className="text-left font-medium py-1.5">{t("analytics.product")}</th>
                                        <th className="text-right font-medium py-1.5">{t("analytics.stock")}</th>
                                        <th className="text-right font-medium py-1.5">{t("analytics.notSold")}</th>
                                        <th className="text-right font-medium py-1.5">{t("analytics.value")}</th>
                                    </tr></thead>
                                    <tbody>
                                        {data.dead_stock.map(d => (
                                            <tr key={d.product_id} className="border-b border-border/40">
                                                <td className="py-1.5 text-foreground">{d.name}</td>
                                                <td className="py-1.5 text-right font-mono text-foreground">{num(d.stock)}</td>
                                                <td className="py-1.5 text-right text-muted-foreground">
                                                    {d.days_since_sale === null ? t("analytics.never") : `${d.days_since_sale}d`}
                                                </td>
                                                <td className="py-1.5 text-right font-mono text-foreground">{eur(d.value_cost)}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </div>
                    </div>

                    {/* Mermas y bajas */}
                    <div className="space-y-4">
                        <h2 className="flex items-center gap-2 text-base font-semibold text-foreground">
                            <PackageMinus className="w-4 h-4 text-rose-400" /> {t("analytics.mermasTitle", { days: data.merma_days })}
                        </h2>

                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                            <KpiCard
                                title={t("analytics.bajasUnits")}
                                value={num(data.bajas.total_units)}
                                icon={PackageMinus}
                                className={data.bajas.total_units > 0 ? "border-rose-500/20" : ""}
                            />
                            <KpiCard title={t("analytics.bajasValue")} value={eur(data.bajas.total_value_eur)} icon={Coins} />
                            <KpiCard title={t("analytics.boxBajas")} value={num(data.box_bajas_units)} icon={Boxes} />
                            <KpiCard
                                title={t("analytics.belowMin")}
                                value={`${data.below_min.count} · ${eur(data.below_min.value_eur)}`}
                                icon={AlertTriangle}
                                className={data.below_min.count > 0 ? "border-amber-500/20" : ""}
                            />
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                            {/* Por motivo */}
                            <div className="rounded-lg border border-border bg-card p-4">
                                <h3 className="flex items-center gap-2 text-sm font-medium text-foreground mb-3">
                                    <PackageMinus className="w-4 h-4 text-rose-400" /> {t("analytics.byReason")}
                                </h3>
                                {data.bajas.by_reason.length === 0 ? (
                                    <p className="text-xs text-muted-foreground">{t("analytics.noBajas")} 👍</p>
                                ) : (
                                    <table className="w-full text-sm">
                                        <thead><tr className="text-xs text-muted-foreground border-b border-border">
                                            <th className="text-left font-medium py-1.5">{t("analytics.reasonLabel")}</th>
                                            <th className="text-right font-medium py-1.5">{t("analytics.units")}</th>
                                            <th className="text-right font-medium py-1.5">{t("analytics.value")}</th>
                                        </tr></thead>
                                        <tbody>
                                            {data.bajas.by_reason.map(r => (
                                                <tr key={r.reason} className="border-b border-border/40">
                                                    <td className="py-1.5 text-foreground">{reasonLabel(r.reason)}</td>
                                                    <td className="py-1.5 text-right font-mono text-foreground">{num(r.units)}</td>
                                                    <td className="py-1.5 text-right font-mono text-foreground">{eur(r.value_eur)}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                )}
                            </div>

                            {/* Productos con más mermas */}
                            <div className="rounded-lg border border-border bg-card p-4">
                                <h3 className="flex items-center gap-2 text-sm font-medium text-foreground mb-3">
                                    <Package className="w-4 h-4 text-rose-400" /> {t("analytics.topMermas")}
                                </h3>
                                {data.bajas.top_products.length === 0 ? (
                                    <p className="text-xs text-muted-foreground">{t("analytics.noBajas")} 👍</p>
                                ) : (
                                    <table className="w-full text-sm">
                                        <thead><tr className="text-xs text-muted-foreground border-b border-border">
                                            <th className="text-left font-medium py-1.5">{t("analytics.product")}</th>
                                            <th className="text-right font-medium py-1.5">{t("analytics.units")}</th>
                                            <th className="text-right font-medium py-1.5">{t("analytics.value")}</th>
                                        </tr></thead>
                                        <tbody>
                                            {data.bajas.top_products.map(p => (
                                                <tr key={p.product_id} className="border-b border-border/40">
                                                    <td className="py-1.5 text-foreground">{p.name}</td>
                                                    <td className="py-1.5 text-right font-mono text-foreground">{num(p.units)}</td>
                                                    <td className="py-1.5 text-right font-mono text-foreground">{eur(p.value_eur)}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                )}
                            </div>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
