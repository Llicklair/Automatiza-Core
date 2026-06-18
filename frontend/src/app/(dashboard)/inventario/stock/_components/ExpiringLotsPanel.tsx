"use client";

import { useEffect, useState } from "react";
import { Loader2, CalendarClock } from "lucide-react";
import { useTranslations } from "next-intl";
import { lots as lotsApi, type ExpiringLot } from "@/lib/api/inventory_lots";

const fmt = (n: number) => n.toLocaleString("es-ES");

const RANGES = [7, 15, 30, 60];

export function ExpiringLotsPanel() {
    const t = useTranslations("inventario");
    const [items, setItems] = useState<ExpiringLot[]>([]);
    const [loading, setLoading] = useState(true);
    const [days, setDays] = useState(30);

    useEffect(() => {
        let active = true;
        setLoading(true);
        lotsApi.expiring(days)
            .then(data => { if (active) setItems(data); })
            .catch(() => { if (active) setItems([]); })
            .finally(() => { if (active) setLoading(false); });
        return () => { active = false; };
    }, [days]);

    const expired = items.filter(i => i.severity === "error").length;

    return (
        <div className="rounded-lg border border-border bg-card p-4 space-y-3">
            <div className="flex items-center justify-between gap-3 flex-wrap">
                <h3 className="flex items-center gap-2 text-sm font-medium text-foreground">
                    <CalendarClock className="w-4 h-4 text-amber-400" />
                    {t("expiring.title")}
                    {!loading && items.length > 0 && (
                        <span className="text-xs text-muted-foreground">
                            ({t("expiring.summary", { count: items.length, days })}{expired > 0 ? ` · ${t("expiring.expiredCount", { count: expired })}` : ""})
                        </span>
                    )}
                </h3>
                <div className="flex items-center gap-1">
                    {RANGES.map(r => (
                        <button
                            key={r}
                            type="button"
                            onClick={() => setDays(r)}
                            className={`text-xs px-2 py-1 rounded-md border transition-colors ${days === r
                                ? "bg-primary/15 border-primary/40 text-foreground"
                                : "border-border text-muted-foreground hover:text-foreground"}`}
                        >
                            {r}d
                        </button>
                    ))}
                </div>
            </div>

            {loading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
                    <Loader2 className="w-4 h-4 animate-spin" /> {t("expiring.loading")}
                </div>
            ) : items.length === 0 ? (
                <p className="text-xs text-muted-foreground py-2">
                    {t("expiring.empty", { days })} 👍
                </p>
            ) : (
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="text-xs text-muted-foreground border-b border-border">
                                <th className="text-left font-medium py-1.5">{t("expiring.colProduct")}</th>
                                <th className="text-left font-medium py-1.5">{t("expiring.colLot")}</th>
                                <th className="text-left font-medium py-1.5">{t("expiring.colExpiry")}</th>
                                <th className="text-right font-medium py-1.5">{t("expiring.colQuantity")}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {items.map(it => {
                                const cls = it.severity === "error" ? "text-rose-400" : "text-amber-400";
                                const when = it.days_left < 0
                                    ? t("expiring.whenExpired", { days: Math.abs(it.days_left) })
                                    : it.days_left === 0 ? t("expiring.whenToday") : t("expiring.whenIn", { days: it.days_left });
                                return (
                                    <tr key={it.id} className="border-b border-border/40">
                                        <td className="py-1.5 text-foreground">{it.product_name}</td>
                                        <td className="py-1.5 font-mono text-muted-foreground">{it.lot_number}</td>
                                        <td className={`py-1.5 font-mono ${cls}`}>
                                            {it.expiry_date} <span className="text-xs">({when})</span>
                                        </td>
                                        <td className="py-1.5 text-right font-mono text-foreground">{fmt(it.quantity)}</td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
