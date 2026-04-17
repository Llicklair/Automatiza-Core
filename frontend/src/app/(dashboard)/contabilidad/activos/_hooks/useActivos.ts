"use client";

import { useEffect, useState } from "react";
import { api, type FixedAsset } from "@/lib/api";
import { logError } from "@/lib/logger";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";

export type FormState = {
    name: string; category: string; description: string;
    purchase_date: string; purchase_value: string;
    useful_life_years: string; residual_value: string;
    account_code: string; reference_invoice: string; notes: string;
};

export const emptyForm = (): FormState => ({
    name: "", category: "equipment", description: "",
    purchase_date: new Date().toISOString().slice(0, 10),
    purchase_value: "", useful_life_years: "5", residual_value: "0",
    account_code: "217", reference_invoice: "", notes: "",
});

export function calcDepreciation(asset: FixedAsset): number {
    const depreciable = Number(asset.purchase_value) - Number(asset.residual_value);
    const monthlyRate = depreciable / (Number(asset.useful_life_years) * 12);
    const purchaseDate = new Date(asset.purchase_date);
    const today = new Date();
    const months = Math.max(0,
        (today.getFullYear() - purchaseDate.getFullYear()) * 12 +
        (today.getMonth() - purchaseDate.getMonth())
    );
    return Math.min(depreciable, monthlyRate * months);
}

export function useActivos() {
    const toast = useToastStore();
    const [assets, setAssets] = useState<FixedAsset[]>([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [form, setForm] = useState<FormState>(emptyForm());
    const [saving, setSaving] = useState(false);
    const [deletingId, setDeletingId] = useState<string | null>(null);

    useEffect(() => {
        api.accounting.assets.list()
            .then(setAssets)
            .catch(err => logError("contabilidad/activos", err))
            .finally(() => setLoading(false));
    }, []);

    const openCreate = () => { setEditingId(null); setForm(emptyForm()); setShowModal(true); };

    const openEdit = (a: FixedAsset) => {
        setEditingId(a.id);
        setForm({
            name: a.name, category: a.category || "other", description: a.description || "",
            purchase_date: a.purchase_date.slice(0, 10),
            purchase_value: String(a.purchase_value),
            useful_life_years: String(a.useful_life_years),
            residual_value: String(a.residual_value),
            account_code: a.account_code || "213",
            reference_invoice: a.reference_invoice || "",
            notes: a.notes || "",
        });
        setShowModal(true);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);
        const payload = {
            name: form.name,
            category: form.category,
            description: form.description || null,
            purchase_date: form.purchase_date,
            purchase_value: parseFloat(form.purchase_value),
            useful_life_years: parseFloat(form.useful_life_years),
            residual_value: parseFloat(form.residual_value) || 0,
            account_code: form.account_code || null,
            reference_invoice: form.reference_invoice || null,
            notes: form.notes || null,
        };
        try {
            if (editingId) {
                const updated = await api.accounting.assets.update(editingId, payload);
                setAssets(prev => prev.map(a => a.id === editingId ? updated : a));
            } else {
                const created = await api.accounting.assets.create(payload);
                setAssets(prev => [created, ...prev]);
            }
            setShowModal(false);
        } catch (err: any) {
            toast.error(err?.message || "Error guardando activo");
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (id: string, name: string) => {
        if (!await showConfirm({ message: `¿Eliminar "${name}"? Esta acción no se puede deshacer.`, confirmLabel: "Eliminar", confirmVariant: "danger" })) return;
        setDeletingId(id);
        try {
            await api.accounting.assets.delete(id);
            setAssets(prev => prev.filter(a => a.id !== id));
        } catch (err: any) {
            toast.error(err?.message || "Error eliminando activo");
        } finally {
            setDeletingId(null);
        }
    };

    const totalValue = assets.reduce((s, a) => s + Number(a.purchase_value), 0);
    const totalDepreciation = assets.reduce((s, a) => s + calcDepreciation(a), 0);
    const netBookValue = totalValue - totalDepreciation;

    const setField = (field: keyof FormState, val: string) => setForm(prev => ({ ...prev, [field]: val }));

    return {
        assets, loading, showModal, setShowModal,
        editingId, form, saving, deletingId,
        openCreate, openEdit, handleSubmit, handleDelete, setField,
        totalValue, totalDepreciation, netBookValue,
    };
}
