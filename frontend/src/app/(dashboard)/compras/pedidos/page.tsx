"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { ShoppingBag, Plus, Search, Loader2, ChevronDown, Package, Calendar, Check, Truck, Trash2 } from "lucide-react";
import { usePedidosCompra } from "./_hooks/usePedidosCompra";
import { NuevoPedidoModal } from "./_components/NuevoPedidoModal";
import { RecibirModal } from "./_components/RecibirModal";
import { type PurchaseOrder } from "@/lib/api";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageContainer } from "@/components/shared/PageContainer";

const fmt = (n: number) => n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });

const STATUS_MAP: Record<string, { color: string; bg: string; border: string }> = {
    draft:     { color: "text-muted-foreground", bg: "bg-muted",          border: "border-border" },
    sent:      { color: "text-blue-400",         bg: "bg-blue-500/10",     border: "border-blue-500/20" },
    confirmed: { color: "text-primary",          bg: "bg-primary/10",      border: "border-primary/20" },
    partially_received: { color: "text-amber-400", bg: "bg-amber-500/10", border: "border-amber-500/20" },
    received:  { color: "text-emerald-400",      bg: "bg-emerald-500/10",  border: "border-emerald-500/20" },
    cancelled: { color: "text-rose-400",         bg: "bg-rose-500/10",     border: "border-rose-500/20" },
};

const STATUS_FLOW: Record<string, string> = { draft: "sent", sent: "confirmed", confirmed: "received" };

export default function PedidosCompraPage() {
    const {
        orders, suppliers, products, loading, search, setSearch,
        showModal, setShowModal, expandedId, setExpandedId,
        saving, deletingId, form, setForm, filtered,
        lineTotal, orderTotal, openNew, setLine,
        handleSubmit, handleAdvance, handleCancel, handleDelete, load,
    } = usePedidosCompra();

    const t = useTranslations("compras.pedidos");
    const [receiveOrder, setReceiveOrder] = useState<PurchaseOrder | null>(null);

    return (
        <PageContainer>
            <PageHeader
                title={t("title")}
                description={t("description")}
                icon={ShoppingBag}
                actions={
                    <Button onClick={openNew}>
                        <Plus className="w-4 h-4 mr-2" /> {t("newOrder")}
                    </Button>
                }
            />

            <div className="grid grid-cols-3 gap-4">
                {[
                    { label: t("stats.pendingReceive"), value: orders.filter(o => ["sent", "confirmed"].includes(o.status)).length, color: "text-amber-400" },
                    { label: t("stats.received"),       value: orders.filter(o => o.status === "received").length,                  color: "text-emerald-400" },
                    { label: t("stats.committedTotal"), value: fmt(orders.filter(o => o.status !== "cancelled").reduce((a, o) => a + o.amount_total, 0)), color: "text-foreground" },
                ].map(stat => (
                    <div key={stat.label} className="bg-card border border-border rounded-2xl p-5">
                        <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">{stat.label}</p>
                        <p className={`text-xl font-bold ${stat.color}`}>{stat.value}</p>
                    </div>
                ))}
            </div>

            <div className="relative">
                <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                <Input
                    placeholder={t("searchPlaceholder")}
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    className="pl-9"
                />
            </div>

            {loading ? (
                <div className="flex items-center justify-center py-24 text-muted-foreground gap-2">
                    <Loader2 className="w-5 h-5 animate-spin" /> {t("loading")}
                </div>
            ) : filtered.length === 0 ? (
                <div className="bg-card border border-border rounded-2xl p-16 flex flex-col items-center text-center">
                    <ShoppingBag className="w-12 h-12 text-muted-foreground mb-4" />
                    <h2 className="text-lg font-bold text-foreground mb-2">{orders.length === 0 ? t("emptyTitle") : t("noResultsTitle")}</h2>
                    <p className="text-sm text-muted-foreground max-w-sm">
                        {orders.length === 0 ? t("emptyDescription") : t("noResultsDescription", { search })}
                    </p>
                    {orders.length === 0 && (
                        <Button onClick={openNew} className="mt-6">{t("createOrder")}</Button>
                    )}
                </div>
            ) : (
                <div className="space-y-3">
                    {filtered.map(order => {
                        const st = STATUS_MAP[order.status] || STATUS_MAP.draft;
                        const nextStatus = STATUS_FLOW[order.status];
                        const isExpanded = expandedId === order.id;

                        return (
                            <div key={order.id} className="bg-card border border-border rounded-2xl overflow-hidden">
                                <div className="flex items-center gap-4 px-6 py-4">
                                    <button onClick={() => setExpandedId(isExpanded ? null : order.id)} className="flex-1 flex items-center gap-4 text-left">
                                        <div className={`${st.bg} ${st.border} border rounded-xl p-2 flex-shrink-0`}>
                                            <Truck className={`w-4 h-4 ${st.color}`} />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <p className="text-sm font-bold text-foreground font-mono">{order.order_number || t("noNumber")}</p>
                                                <span className={`text-xs px-2 py-0.5 rounded-full ${st.bg} ${st.border} border ${st.color}`}>{t(`status.${order.status}`)}</span>
                                            </div>
                                            <p className="text-xs text-muted-foreground mt-0.5">{order.supplier?.name || t("unknownSupplier")}</p>
                                        </div>
                                        <div className="text-right flex-shrink-0">
                                            <p className="text-sm font-bold text-foreground">{fmt(order.amount_total)}</p>
                                            <p className="text-xs text-muted-foreground">{new Date(order.date).toLocaleDateString("es-ES")}</p>
                                        </div>
                                        <ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform ${isExpanded ? "rotate-180" : ""}`} />
                                    </button>
                                    <div className="flex items-center gap-2 flex-shrink-0">
                                        {nextStatus && (
                                            <Button size="sm" variant="ghost" className="h-7 text-xs bg-emerald-600/20 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-600/30" onClick={() => handleAdvance(order)}>
                                                <Check className="w-3 h-3 mr-1" /> {t(`status.${nextStatus}`)}
                                            </Button>
                                        )}
                                        {["sent", "confirmed", "partially_received"].includes(order.status) && (
                                            <Button size="sm" variant="ghost" className="h-7 text-xs bg-blue-600/20 text-blue-400 border border-blue-500/20 hover:bg-blue-600/30" onClick={() => setReceiveOrder(order)}>
                                                <Package className="w-3 h-3 mr-1" /> {t("receive")}
                                            </Button>
                                        )}
                                        {!["cancelled", "received"].includes(order.status) && (
                                            <Button size="sm" variant="ghost" className="h-7 text-xs text-muted-foreground hover:text-rose-400 hover:bg-rose-500/10" onClick={() => handleCancel(order)}>{t("cancel")}</Button>
                                        )}
                                        <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-rose-400 hover:bg-rose-500/10" onClick={() => handleDelete(order.id)} disabled={deletingId === order.id} aria-label={t("deleteOrder")}>
                                            {deletingId === order.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" /> : <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />}
                                        </Button>
                                    </div>
                                </div>

                                {isExpanded && (
                                    <div className="border-t border-border/50 px-6 py-4 bg-muted/40">
                                        {order.expected_delivery && (
                                            <p className="text-xs text-muted-foreground mb-3 flex items-center gap-1.5">
                                                <Calendar className="w-3 h-3" /> {t("expectedDelivery", { date: new Date(order.expected_delivery).toLocaleDateString("es-ES") })}
                                            </p>
                                        )}
                                        <div className="space-y-2">
                                            {(order.lines || []).map((line, i) => (
                                                <div key={i} className="flex items-center gap-4 text-sm">
                                                    <Package className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                                                    <span className="flex-1 text-foreground">{line.description}</span>
                                                    <span className="text-muted-foreground font-mono">{line.quantity} × {fmt(line.unit_price)}</span>
                                                    <span className="text-muted-foreground font-mono w-24 text-right">{fmt(line.total || 0)}</span>
                                                </div>
                                            ))}
                                        </div>
                                        {order.notes && <p className="text-xs text-muted-foreground mt-3 italic">{order.notes}</p>}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}

            <NuevoPedidoModal
                open={showModal}
                onClose={() => setShowModal(false)}
                form={form}
                setForm={setForm}
                suppliers={suppliers}
                products={products}
                saving={saving}
                orderTotal={orderTotal}
                lineTotal={lineTotal}
                setLine={setLine}
                onSubmit={handleSubmit}
            />

            <RecibirModal order={receiveOrder} onClose={() => setReceiveOrder(null)} onReceived={load} />
        </PageContainer>
    );
}
