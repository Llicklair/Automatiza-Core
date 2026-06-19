"use client";

import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import type { RemesaItem, RemesaType } from "../_hooks/useRemesas";
import { TYPE_CONFIG } from "../_hooks/useRemesas";

const fmt = (v: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(v);

interface RemesaSummaryProps {
    selected: RemesaItem[];
    totalSelected: number;
}

export default function RemesaSummary({ selected, totalSelected }: RemesaSummaryProps) {
    const t = useTranslations("tesoreria");
    return (
        <div className="bg-card border border-border rounded-2xl p-5">
            <h3 className="text-sm font-semibold text-foreground mb-4">{t("remesaSummary.title")}</h3>
            {selected.length === 0 ? (
                <p className="text-xs text-muted-foreground text-center py-4">{t("remesaSummary.empty")}</p>
            ) : (
                <div className="space-y-2">
                    {(["cobros", "pagos", "nominas"] as RemesaType[]).map(type => {
                        const tItems = selected.filter(i => i.type === type);
                        if (!tItems.length) return null;
                        return (
                            <div key={type} className="flex items-center justify-between text-sm">
                                <span className={cn("text-xs", TYPE_CONFIG[type].color)}>{TYPE_CONFIG[type].label} ({tItems.length})</span>
                                <span className="text-foreground font-medium">{fmt(tItems.reduce((s, i) => s + i.amount, 0))}</span>
                            </div>
                        );
                    })}
                    <div className="pt-3 mt-3 border-t border-border flex items-center justify-between">
                        <span className="text-sm font-semibold text-foreground">{t("remesaSummary.total")}</span>
                        <span className="text-base font-bold text-foreground">{fmt(totalSelected)}</span>
                    </div>
                    <div className="text-xs text-muted-foreground pt-1">{t("remesaSummary.includedCount", { count: selected.length })}</div>
                </div>
            )}
        </div>
    );
}
