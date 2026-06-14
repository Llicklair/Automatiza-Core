"use client";

import { useEffect, useState } from "react";
import { api, Product } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";
import { useTranslations } from "next-intl";

export type FormState = {
    name: string; sku: string; description: string;
    price: string; tax_percentage: string;
};

export const emptyForm = (): FormState => ({
    name: "", sku: "", description: "", price: "", tax_percentage: "21"
});

export const fmt = (val: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(val);

export function useServicios() {
    const toast = useToastStore();
    const t = useTranslations("ventas");
    const tc = useTranslations("common");
    const [services, setServices] = useState<Product[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [showModal, setShowModal] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [form, setForm] = useState<FormState>(emptyForm());
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [deletingId, setDeletingId] = useState<string | null>(null);

    const loadData = async () => {
        setIsLoading(true);
        try {
            const data = await api.erp.products.list({ limit: 200 });
            setServices(data.filter(p => p.item_type === "service"));
        } catch (error) {
            logError("ventas/servicios/page", error);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => { loadData(); }, []);

    const openCreate = () => { setEditingId(null); setForm(emptyForm()); setShowModal(true); };
    const openEdit = (s: Product) => {
        setEditingId(s.id);
        setForm({ name: s.name, sku: s.sku || "", description: s.description || "", price: String(s.price), tax_percentage: String(s.tax_percentage) });
        setShowModal(true);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSubmitting(true);
        const payload = {
            name: form.name, sku: form.sku || null, description: form.description || null,
            price: parseFloat(form.price) || 0,
            tax_percentage: parseFloat(form.tax_percentage),
            item_type: "service",
        };
        try {
            if (editingId) {
                const updated = await api.erp.products.update(editingId, payload);
                setServices(prev => prev.map(s => s.id === editingId ? updated : s));
            } else {
                const created = await api.erp.products.create(payload);
                setServices(prev => [created, ...prev]);
            }
            setShowModal(false);
        } catch (err: any) {
            toast.error(err?.message || t("serviceErrorSaving"));
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleDelete = async (id: string, name: string) => {
        if (!await showConfirm({ message: t("serviceDeleteConfirm", { name }), confirmLabel: tc("delete"), confirmVariant: "danger" })) return;
        setDeletingId(id);
        try {
            await api.erp.products.delete(id);
            setServices(prev => prev.filter(s => s.id !== id));
        } catch (err: any) {
            toast.error(err?.message || t("serviceErrorDeleting"));
        } finally {
            setDeletingId(null);
        }
    };

    const filtered = services.filter(s => {
        const q = search.toLowerCase();
        return s.name.toLowerCase().includes(q) || (s.sku || "").toLowerCase().includes(q) || (s.description || "").toLowerCase().includes(q);
    });

    return {
        services, isLoading, search, setSearch,
        showModal, setShowModal,
        editingId, form, setForm,
        isSubmitting, deletingId,
        openCreate, openEdit, handleSubmit, handleDelete,
        filtered,
    };
}
