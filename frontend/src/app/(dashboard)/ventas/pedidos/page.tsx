"use client";

import { usePedidos } from "./_hooks/usePedidos";
import OrderCard from "./_components/OrderCard";
import OrderModal from "./_components/OrderModal";
import { ClipboardList, Plus, Search, Loader2 } from "lucide-react";

export default function PedidosPage() {
    const {
        orders, filtered, loading, search, setSearch,
        showModal, setShowModal, expandedId, toggleExpanded,
        saving, deletingId,
        form, setForm, clients, products,
        setLine, addLine, removeLine, lineTotal, orderTotal,
        openNew, handleSubmit, handleAdvanceStatus, handleCancel, handleDelete,
        byStatus, t, tc,
    } = usePedidos();

    return (
        <div className="p-8 max-w-6xl mx-auto space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-foreground tracking-tight">{t("orders")}</h1>
                    <p className="mt-1 text-sm text-muted-foreground">{t("ordersDescription")}</p>
                </div>
                <button onClick={openNew} className="flex items-center gap-2 bg-primary hover:bg-primary text-foreground text-sm font-medium px-4 py-2.5 rounded-xl transition-colors">
                    <Plus className="w-4 h-4" /> {t("newOrder")}
                </button>
            </div>

            <div className="grid grid-cols-3 gap-4">
                {[
                    { label: t("confirmed"), value: byStatus("confirmed") + byStatus("processing"), color: "text-blue-400" },
                    { label: t("inTransit"), value: byStatus("shipped"), color: "text-primary" },
                    { label: t("delivered"), value: byStatus("delivered"), color: "text-emerald-400" },
                ].map(stat => (
                    <div key={stat.label} className="bg-card border border-border rounded-2xl p-5">
                        <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">{stat.label}</p>
                        <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
                    </div>
                ))}
            </div>

            <div className="relative">
                <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                <input type="text" placeholder={t("searchOrderPlaceholder")} value={search} onChange={e => setSearch(e.target.value)}
                    className="w-full bg-card border border-border text-foreground text-sm rounded-xl pl-9 pr-4 py-2.5 focus:outline-none focus:border-primary transition-colors" />
            </div>

            {loading ? (
                <div className="flex items-center justify-center py-24 text-muted-foreground gap-2">
                    <Loader2 className="w-5 h-5 animate-spin" /> {t("orderLoading")}
                </div>
            ) : filtered.length === 0 ? (
                <div className="bg-card border border-border rounded-2xl p-16 flex flex-col items-center text-center">
                    <ClipboardList className="w-12 h-12 text-muted-foreground mb-4" />
                    <h2 className="text-lg font-bold text-foreground mb-2">{orders.length === 0 ? t("orderEmptyTitle") : tc("noResults")}</h2>
                    <p className="text-sm text-muted-foreground max-w-md">
                        {orders.length === 0 ? t("orderEmptyDescription") : t("orderNoMatch", { search })}
                    </p>
                    {orders.length === 0 && (
                        <button onClick={openNew} className="mt-6 bg-primary hover:bg-primary text-foreground text-sm px-4 py-2 rounded-xl transition-colors">{t("createOrder")}</button>
                    )}
                </div>
            ) : (
                <div className="space-y-3">
                    {filtered.map(order => (
                        <OrderCard
                            key={order.id}
                            order={order}
                            isExpanded={expandedId === order.id}
                            deletingId={deletingId}
                            onToggle={toggleExpanded}
                            onAdvance={handleAdvanceStatus}
                            onCancel={handleCancel}
                            onDelete={handleDelete}
                            t={t}
                            tc={tc}
                        />
                    ))}
                </div>
            )}

            {showModal && (
                <OrderModal
                    form={form} setForm={setForm}
                    clients={clients} products={products}
                    saving={saving} lineTotal={lineTotal} orderTotal={orderTotal}
                    onSubmit={handleSubmit} onClose={() => setShowModal(false)}
                    setLine={setLine} addLine={addLine} removeLine={removeLine}
                    t={t} tc={tc}
                />
            )}
        </div>
    );
}
