"use client";

import { useEffect, useState } from "react";
import { api, type PurchaseOrder, type Client, type Product, type PurchaseOrderLine } from "@/lib/api";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";

const EMPTY_LINE: PurchaseOrderLine = { description: "", quantity: 1, unit_price: 0, tax_percentage: 21 };

const STATUS_FLOW: Record<string, string> = {
    draft: "sent", sent: "confirmed", confirmed: "received"
};

export type PedidoForm = {
    supplier_id: string;
    expected_delivery: string;
    notes: string;
    lines: PurchaseOrderLine[];
};

export function usePedidosCompra() {
    const [orders, setOrders] = useState<PurchaseOrder[]>([]);
    const [suppliers, setSuppliers] = useState<Client[]>([]);
    const [products, setProducts] = useState<Product[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [showModal, setShowModal] = useState(false);
    const [expandedId, setExpandedId] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const [deletingId, setDeletingId] = useState<string | null>(null);

    const [form, setForm] = useState<PedidoForm>({
        supplier_id: "", expected_delivery: "", notes: "",
        lines: [{ ...EMPTY_LINE }],
    });

    const load = async () => {
        try {
            const [ordersData, suppliersData, productsData] = await Promise.all([
                api.erp.purchaseOrders.list(),
                api.erp.clients.list({ client_type: "supplier", limit: 200 }),
                api.erp.products.list({ limit: 200 }),
            ]);
            setOrders(ordersData);
            setSuppliers(suppliersData);
            setProducts(productsData);
        } catch (err) { logError("compras/pedidos", err); }
        finally { setLoading(false); }
    };

    useEffect(() => { load(); }, []);

    const openNew = () => {
        setForm({ supplier_id: "", expected_delivery: "", notes: "", lines: [{ ...EMPTY_LINE }] });
        setShowModal(true);
    };

    const setLine = (i: number, field: keyof PurchaseOrderLine, value: any) => {
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

    const lineTotal = (line: PurchaseOrderLine) =>
        line.quantity * line.unit_price * (1 + line.tax_percentage / 100);

    const orderTotal = form.lines.reduce((acc, l) => acc + lineTotal(l), 0);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.supplier_id) return;
        setSaving(true);
        try {
            await api.erp.purchaseOrders.create({
                supplier_id: form.supplier_id,
                expected_delivery: form.expected_delivery || undefined,
                notes: form.notes || undefined,
                lines: form.lines.filter(l => l.description.trim()),
            } as any);
            setShowModal(false);
            setLoading(true);
            load();
        } catch (err) { logError("compras/pedidos", err); }
        finally { setSaving(false); }
    };

    const handleAdvance = async (order: PurchaseOrder) => {
        const next = STATUS_FLOW[order.status];
        if (!next) return;
        try {
            const updated = await api.erp.purchaseOrders.update(order.id, { status: next });
            setOrders(prev => prev.map(o => o.id === order.id ? updated : o));
        } catch (err) { logError("compras/pedidos", err); }
    };

    const handleCancel = async (order: PurchaseOrder) => {
        if (!await showConfirm({ message: "¿Cancelar este pedido?", confirmLabel: "Cancelar", confirmVariant: "danger" })) return;
        try {
            const updated = await api.erp.purchaseOrders.update(order.id, { status: "cancelled" });
            setOrders(prev => prev.map(o => o.id === order.id ? updated : o));
        } catch (err) { logError("compras/pedidos", err); }
    };

    const handleDelete = async (id: string) => {
        if (!await showConfirm({ message: "¿Eliminar definitivamente?", confirmLabel: "Eliminar", confirmVariant: "danger" })) return;
        setDeletingId(id);
        try {
            await api.erp.purchaseOrders.delete(id);
            setOrders(prev => prev.filter(o => o.id !== id));
        } catch (err) { logError("compras/pedidos", err); }
        finally { setDeletingId(null); }
    };

    const q = search.toLowerCase();
    const filtered = orders.filter(o =>
        !q ||
        (o.order_number || "").toLowerCase().includes(q) ||
        (o.supplier?.name || "").toLowerCase().includes(q)
    );

    return {
        orders, suppliers, products, loading, search, setSearch,
        showModal, setShowModal, expandedId, setExpandedId,
        saving, deletingId, form, setForm,
        filtered, lineTotal, orderTotal,
        openNew, setLine, handleSubmit, handleAdvance, handleCancel, handleDelete,
    };
}
