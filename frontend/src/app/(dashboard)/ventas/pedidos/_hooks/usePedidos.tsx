"use client";

import { useEffect, useState, useCallback } from "react";
import { api, type SalesOrder, type Client, type Product, type SalesOrderLine } from "@/lib/api";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";
import { useTranslations } from "next-intl";

export const fmt = (n: number) => n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });

export const STATUS_MAP: Record<string, { label: string; color: string; bg: string; border: string }> = {
    draft: { label: "draft", color: "text-muted-foreground", bg: "bg-muted", border: "border-border" },
    confirmed: { label: "confirmed", color: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/20" },
    processing: { label: "inProcess", color: "text-amber-400", bg: "bg-amber-500/10", border: "border-amber-500/20" },
    shipped: { label: "shipped", color: "text-primary", bg: "bg-primary/10", border: "border-primary/20" },
    delivered: { label: "delivered", color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20" },
    cancelled: { label: "cancelled", color: "text-rose-400", bg: "bg-rose-500/10", border: "border-rose-500/20" },
};

export const STATUS_FLOW: Record<string, string> = {
    draft: "confirmed", confirmed: "processing", processing: "shipped", shipped: "delivered",
};

const EMPTY_LINE: SalesOrderLine = { description: "", quantity: 1, unit_price: 0, discount_percentage: 0, tax_percentage: 21 };

export function usePedidos() {
    const t = useTranslations("ventas");
    const tc = useTranslations("common");

    const [orders, setOrders] = useState<SalesOrder[]>([]);
    const [clients, setClients] = useState<Client[]>([]);
    const [products, setProducts] = useState<Product[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [showModal, setShowModal] = useState(false);
    const [expandedId, setExpandedId] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const [deletingId, setDeletingId] = useState<string | null>(null);

    const [form, setForm] = useState({
        client_id: "",
        expected_delivery: "",
        notes: "",
        lines: [{ ...EMPTY_LINE }] as SalesOrderLine[],
    });

    const load = useCallback(async () => {
        try {
            const [ordersData, clientsData, productsData] = await Promise.all([
                api.erp.orders.list(),
                api.erp.clients.list({ limit: 200 }),
                api.erp.products.list({ limit: 200 }),
            ]);
            setOrders(ordersData);
            setClients(clientsData.filter(c => c.client_type === "customer"));
            setProducts(productsData);
        } catch (err) {
            logError("ventas/pedidos/page", err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    const openNew = () => {
        setForm({ client_id: "", expected_delivery: "", notes: "", lines: [{ ...EMPTY_LINE }] });
        setShowModal(true);
    };

    const setLine = (i: number, field: keyof SalesOrderLine, value: any) => {
        setForm(f => {
            const lines = [...f.lines];
            lines[i] = { ...lines[i], [field]: value };
            if (field === "product_id") {
                const prod = products.find(p => p.id === value);
                if (prod) {
                    lines[i].description = prod.name;
                    lines[i].unit_price = prod.price;
                    lines[i].tax_percentage = prod.tax_percentage;
                }
            }
            return { ...f, lines };
        });
    };

    const addLine = () => setForm(f => ({ ...f, lines: [...f.lines, { ...EMPTY_LINE }] }));
    const removeLine = (i: number) => setForm(f => ({ ...f, lines: f.lines.filter((_, idx) => idx !== i) }));

    const lineTotal = (line: SalesOrderLine) => {
        const base = line.quantity * line.unit_price * (1 - (line.discount_percentage || 0) / 100);
        return base * (1 + line.tax_percentage / 100);
    };

    const orderTotal = form.lines.reduce((acc, l) => acc + lineTotal(l), 0);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.client_id || form.lines.every(l => !l.description)) return;
        setSaving(true);
        try {
            await api.erp.orders.create({
                client_id: form.client_id,
                expected_delivery: form.expected_delivery || undefined,
                notes: form.notes || undefined,
                lines: form.lines.filter(l => l.description.trim()),
            } as any);
            setShowModal(false);
            setLoading(true);
            load();
        } catch (err) {
            logError("ventas/pedidos/page", err);
        } finally {
            setSaving(false);
        }
    };

    const handleAdvanceStatus = async (order: SalesOrder) => {
        const nextStatus = STATUS_FLOW[order.status];
        if (!nextStatus) return;
        try {
            const updated = await api.erp.orders.update(order.id, { status: nextStatus });
            setOrders(prev => prev.map(o => o.id === order.id ? updated : o));
        } catch (err) {
            logError("ventas/pedidos/page", err);
        }
    };

    const handleCancel = async (order: SalesOrder) => {
        if (!await showConfirm({ message: t("orderCancelConfirm"), confirmLabel: tc("cancel"), confirmVariant: "danger" })) return;
        try {
            const updated = await api.erp.orders.update(order.id, { status: "cancelled" });
            setOrders(prev => prev.map(o => o.id === order.id ? updated : o));
        } catch (err) {
            logError("ventas/pedidos/page", err);
        }
    };

    const handleDelete = async (id: string) => {
        if (!await showConfirm({ message: t("orderDeleteConfirm"), confirmLabel: tc("delete"), confirmVariant: "danger" })) return;
        setDeletingId(id);
        try {
            await api.erp.orders.delete(id);
            setOrders(prev => prev.filter(o => o.id !== id));
        } catch (err) {
            logError("ventas/pedidos/page", err);
        } finally {
            setDeletingId(null);
        }
    };

    const toggleExpanded = (id: string) => setExpandedId(prev => prev === id ? null : id);

    const q = search.toLowerCase();
    const filtered = orders.filter(o =>
        !q ||
        (o.order_number || "").toLowerCase().includes(q) ||
        (o.client?.name || "").toLowerCase().includes(q)
    );

    const byStatus = (s: string) => orders.filter(o => o.status === s).length;

    return {
        orders, filtered, loading, search, setSearch,
        showModal, setShowModal, expandedId, toggleExpanded,
        saving, deletingId,
        form, setForm, clients, products,
        setLine, addLine, removeLine, lineTotal, orderTotal,
        openNew, handleSubmit, handleAdvanceStatus, handleCancel, handleDelete,
        byStatus, t, tc,
    };
}
