"use client";

import { useEffect, useState } from "react";
import { api, Product } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";

export type FormState = {
    name: string; sku: string; barcode: string; description: string;
    category: string; location: string; unit: string;
    price: string; cost_price: string; tax_percentage: string;
    item_type: string; is_active: boolean;
};

const emptyForm = (): FormState => ({
    name: "", sku: "", barcode: "", description: "",
    category: "", location: "", unit: "ud",
    price: "", cost_price: "", tax_percentage: "21",
    item_type: "product", is_active: true,
});

export function useCatalogPage() {
    const toast = useToastStore();
    const [products, setProducts] = useState<Product[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    const [showModal, setShowModal] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [form, setForm] = useState<FormState>(emptyForm());
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [deletingId, setDeletingId] = useState<string | null>(null);

    const loadData = async () => {
        setIsLoading(true);
        try { setProducts(await api.erp.products.list({ limit: 200 })); }
        catch { /* silent */ }
        finally { setIsLoading(false); }
    };

    useEffect(() => { loadData(); }, []);

    const openCreate = () => { setEditingId(null); setForm(emptyForm()); setShowModal(true); };
    const openEdit = (p: Product) => {
        setEditingId(p.id);
        setForm({
            name: p.name,
            sku: p.sku || "",
            barcode: p.barcode || "",
            description: p.description || "",
            category: p.category || "",
            location: p.location || "",
            unit: p.unit || "ud",
            price: String(p.price),
            cost_price: p.cost_price != null ? String(p.cost_price) : "",
            tax_percentage: String(p.tax_percentage),
            item_type: p.item_type,
            is_active: p.is_active,
        });
        setShowModal(true);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSubmitting(true);
        const payload = {
            name: form.name,
            sku: form.sku || null,
            barcode: form.barcode || null,
            description: form.description || null,
            category: form.category || null,
            location: form.location || null,
            unit: form.unit || "ud",
            price: parseFloat(form.price) || 0,
            cost_price: form.cost_price ? parseFloat(form.cost_price) : null,
            tax_percentage: parseFloat(form.tax_percentage),
            item_type: form.item_type,
            is_active: form.is_active,
        };
        try {
            if (editingId) {
                const updated = await api.erp.products.update(editingId, payload);
                setProducts(prev => prev.map(p => p.id === editingId ? updated : p));
            } else {
                const created = await api.erp.products.create(payload);
                setProducts(prev => [created, ...prev]);
            }
            setShowModal(false);
        } catch (err: any) {
            toast.error(err?.message || "Error guardando");
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleDelete = async (id: string, name: string) => {
        const confirmed = await showConfirm({
            title: "Eliminar artículo",
            message: `¿Eliminar "${name}"? Esta acción no se puede deshacer.`,
            confirmLabel: "Eliminar",
            cancelLabel: "Cancelar",
            confirmVariant: "danger",
        });
        if (!confirmed) return;
        setDeletingId(id);
        try {
            await api.erp.products.delete(id);
            setProducts(prev => prev.filter(p => p.id !== id));
            toast.success("Artículo eliminado");
        } catch (err: any) {
            toast.error(err?.message || "Error eliminando");
        } finally {
            setDeletingId(null);
        }
    };

    return {
        products, isLoading,
        showModal, setShowModal,
        editingId, form, setForm,
        isSubmitting, deletingId,
        openCreate, openEdit, handleSubmit, handleDelete,
    };
}
