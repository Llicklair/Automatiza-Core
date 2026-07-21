"use client";

import { useState } from "react";
import { api, type SalesOrder } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { fmt, STATUS_MAP, STATUS_FLOW } from "../_hooks/usePedidos";
import {
    ClipboardList, ChevronDown, Package, Calendar, Check,
    Loader2, Tags, Trash2
} from "lucide-react";

interface OrderCardProps {
    order: SalesOrder;
    isExpanded: boolean;
    deletingId: string | null;
    onToggle: (id: string) => void;
    onAdvance: (order: SalesOrder) => void;
    onCancel: (order: SalesOrder) => void;
    onDelete: (id: string) => void;
    t: (key: string, values?: Record<string, string | number | Date>) => string;
    tc: (key: string) => string;
}

export default function OrderCard({
    order, isExpanded, deletingId,
    onToggle, onAdvance, onCancel, onDelete, t, tc,
}: OrderCardProps) {
    const st = STATUS_MAP[order.status] || STATUS_MAP.draft;
    const nextStatus = STATUS_FLOW[order.status];
    const toast = useToastStore();
    const [printing, setPrinting] = useState(false);

    const handlePrintLabels = async () => {
        setPrinting(true);
        try {
            await api.erp.orders.labelsPdf(order.id);
        } catch {
            toast.error(t("printLabelsError"));
        } finally {
            setPrinting(false);
        }
    };

    return (
        <div className="bg-card border border-border rounded-2xl overflow-hidden">
            <div className="flex items-center gap-4 px-6 py-4">
                <button onClick={() => onToggle(order.id)} className="flex-1 flex items-center gap-4 text-left">
                    <div className={`${st.bg} ${st.border} border rounded-xl p-2 flex-shrink-0`}>
                        <ClipboardList className={`w-4 h-4 ${st.color}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                            <p className="text-sm font-bold text-foreground font-mono">{order.order_number || t("orderNoNumber")}</p>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${st.bg} ${st.border} border ${st.color}`}>{t(st.label)}</span>
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5">{order.client?.name || t("unknownClient")}</p>
                    </div>
                    <div className="text-right flex-shrink-0">
                        <p className="text-sm font-bold text-foreground">{fmt(order.amount_total)}</p>
                        <p className="text-xs text-muted-foreground">{new Date(order.date).toLocaleDateString("es-ES")}</p>
                    </div>
                    <ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform ${isExpanded ? "rotate-180" : ""}`} />
                </button>
                <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                        onClick={handlePrintLabels}
                        disabled={printing}
                        className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                        title={t("printLabels")}
                        aria-label={t("printLabels")}
                    >
                        {printing ? <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" /> : <Tags className="w-3.5 h-3.5" aria-hidden="true" />}
                    </button>
                    {nextStatus && (
                        <button
                            onClick={() => onAdvance(order)}
                            className="flex items-center gap-1.5 bg-emerald-600/80 hover:bg-emerald-500 text-foreground text-xs px-3 py-1.5 rounded-lg transition-colors"
                            title={t("orderAdvanceTo", { status: t(STATUS_MAP[nextStatus]?.label ?? "draft") })}
                        >
                            <Check className="w-3 h-3" /> {t(STATUS_MAP[nextStatus]?.label ?? "draft")}
                        </button>
                    )}
                    {order.status !== "cancelled" && order.status !== "delivered" && (
                        <button onClick={() => onCancel(order)} className="text-xs text-muted-foreground hover:text-rose-400 px-2 py-1.5 rounded-lg hover:bg-rose-500/10 transition-colors">
                            {tc("cancel")}
                        </button>
                    )}
                    <button onClick={() => onDelete(order.id)} disabled={deletingId === order.id} className="p-1.5 rounded-lg hover:bg-rose-500/10 text-muted-foreground hover:text-rose-400 transition-colors" aria-label={t("deleteOrderAria")}>
                        {deletingId === order.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" /> : <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />}
                    </button>
                </div>
            </div>

            {isExpanded && (
                <div className="border-t border-border/50 px-6 py-4 bg-muted/40">
                    {order.expected_delivery && (
                        <p className="text-xs text-muted-foreground mb-3 flex items-center gap-1.5">
                            <Calendar className="w-3 h-3" /> {t("expectedDelivery")}: {new Date(order.expected_delivery).toLocaleDateString("es-ES")}
                        </p>
                    )}
                    <div className="space-y-2">
                        {(order.lines || []).map((line, i) => (
                            <div key={i} className="flex items-center gap-4 text-sm">
                                <Package className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                                <span className="flex-1 text-foreground">{line.description}</span>
                                <span className="text-muted-foreground font-mono">{line.quantity} x {fmt(line.unit_price)}</span>
                                <span className="text-muted-foreground font-mono w-24 text-right">{fmt(line.total || 0)}</span>
                            </div>
                        ))}
                    </div>
                    {order.notes && (
                        <p className="text-xs text-muted-foreground mt-3 italic">{order.notes}</p>
                    )}
                </div>
            )}
        </div>
    );
}
