"use client";

import { ArrowUpCircle, ArrowDownCircle, SlidersHorizontal, Loader2, Clock } from "lucide-react";
import { useTranslations } from "next-intl";
import { type Product, type StockMovement } from "@/lib/api";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Card, CardContent } from "@/components/ui/card";

export const MOVEMENT_ICONS: Record<string, React.ReactNode> = {
    entrada: <ArrowUpCircle className="w-4 h-4 text-emerald-400" />,
    salida: <ArrowDownCircle className="w-4 h-4 text-rose-400" />,
    ajuste: <SlidersHorizontal className="w-4 h-4 text-amber-400" />,
};

export const MOVEMENT_COLORS: Record<string, string> = {
    entrada: "text-emerald-400",
    salida: "text-rose-400",
    ajuste: "text-amber-400",
};

const fmt = (n: number) => n.toLocaleString("es-ES");

export function StockStatus({ product }: { product: Product }) {
    const t = useTranslations("inventario");
    const isOut = product.stock_quantity === 0;
    const isLow = product.stock_min_alert > 0 && product.stock_quantity <= product.stock_min_alert;
    if (isOut) return <StatusBadge status="out_of_stock" label={t("stock.statusOut")} />;
    if (isLow) return <StatusBadge status="low_stock" label={t("stock.statusLow")} />;
    return <StatusBadge status="active" label={t("stock.statusOk")} />;
}

export function MovementsPanel({ productId, movements, movementsLoading }: {
    productId: string;
    movements: Record<string, StockMovement[]>;
    movementsLoading: string | null;
}) {
    const t = useTranslations("inventario");
    return (
        <Card className="mx-4 mb-4 mt-1">
            <CardContent className="p-4">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">{t("stock.movementHistory")}</p>
                {movementsLoading === productId ? (
                    <div className="flex items-center gap-2 text-muted-foreground text-sm py-2">
                        <Loader2 className="w-4 h-4 animate-spin" /> {t("stock.loadingShort")}
                    </div>
                ) : !movements[productId] || movements[productId].length === 0 ? (
                    <p className="text-muted-foreground text-sm italic">{t("stock.noMovements")}</p>
                ) : (
                    <div className="space-y-2">
                        {movements[productId].slice(0, 10).map(mov => (
                            <div key={mov.id} className="flex items-center gap-3 text-sm">
                                {MOVEMENT_ICONS[mov.movement_type]}
                                <span className={`font-medium w-14 ${MOVEMENT_COLORS[mov.movement_type]}`}>
                                    {mov.movement_type === "entrada" ? "+" : mov.movement_type === "salida" ? "-" : "="}{Math.abs(mov.quantity)}
                                </span>
                                <span className="text-muted-foreground flex-1">{mov.reference || mov.notes || <span className="italic text-muted-foreground">{t("stock.noReference")}</span>}</span>
                                <span className="text-muted-foreground font-mono text-xs">&rarr; {t("stock.unitsShort", { value: fmt(mov.stock_after) })}</span>
                                <span className="text-muted-foreground text-xs flex items-center gap-1">
                                    <Clock className="w-3 h-3" />
                                    {new Date(mov.created_at).toLocaleDateString("es-ES")}
                                </span>
                            </div>
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
