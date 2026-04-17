"use client";

import { useEffect, useState } from "react";
import { api, Product } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";

type FormState = {
    name: string; sku: string; description: string;
    price: string; tax_percentage: string; item_type: string;
};

const emptyForm = (): FormState => ({
    name: "", sku: "", description: "", price: "", tax_percentage: "21", item_type: "product"
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

    useEffect(() => { loadData(); }, []);

    const loadData = async () => {
        setIsLoading(true);
        try { setProducts(await api.erp.products.list({ limit: 200 })); }
        catch { /* silent */ }
        finally { setIsLoading(false); }
    };

    const openCreate = () => { setEditingId(null); setForm(emptyForm()); setShowModal(true); };
    const openEdit = (p: Product) => {
        setEditingId(p.id);
        setForm({ name: p.name, sku: p.sku || "", description: p.description || "", price: String(p.price), tax_percentage: String(p.tax_percentage), item_type: p.item_type });
        setShowModal(true);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSubmitting(true);
        const payload = {
            name: form.name, sku: form.sku || null, description: form.description || null,
            price: parseFloat(form.price) || 0,
            tax_percentage: parseFloat(form.tax_percentage),
            item_type: form.item_type,
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
