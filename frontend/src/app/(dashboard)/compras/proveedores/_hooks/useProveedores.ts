"use client";

import { useEffect, useState } from "react";
import { api, type Client } from "@/lib/api";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";

const EMPTY_FORM = { name: "", nif: "", email: "", address: "", city: "", postal_code: "" };

export function useProveedores() {
    const [suppliers, setSuppliers] = useState<Client[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [showModal, setShowModal] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [form, setForm] = useState(EMPTY_FORM);
    const [saving, setSaving] = useState(false);
    const [deletingId, setDeletingId] = useState<string | null>(null);

    const load = () =>
        api.erp.clients.list({ client_type: "supplier", limit: 200 })
            .then(setSuppliers)
            .catch(err => logError("compras/proveedores/page", err))
            .finally(() => setLoading(false));

    useEffect(() => { load(); }, []);

    const openNew = () => {
        setForm(EMPTY_FORM);
        setEditingId(null);
        setShowModal(true);
    };

    const openEdit = (s: Client) => {
        setForm({ name: s.name, nif: s.nif || "", email: s.email || "", address: s.address || "", city: s.city || "", postal_code: s.postal_code || "" });
        setEditingId(s.id);
        setShowModal(true);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.name.trim()) return;
        setSaving(true);
        try {
            if (editingId) {
                await api.erp.clients.update(editingId, form);
            } else {
                await api.erp.clients.create({ ...form, client_type: "supplier" });
            }
            setShowModal(false);
            setLoading(true);
            load();
        } catch (err) {
            logError("compras/proveedores/page", err);
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (id: string) => {
        if (!await showConfirm({ message: "¿Eliminar este proveedor?", confirmLabel: "Eliminar", confirmVariant: "danger" })) return;
        setDeletingId(id);
        try {
            await api.erp.clients.delete(id);
            setSuppliers(prev => prev.filter(s => s.id !== id));
        } catch (err) {
            logError("compras/proveedores/page", err);
        } finally {
            setDeletingId(null);
        }
    };

    const q = search.toLowerCase();
    const filtered = suppliers.filter(s =>
        !q || s.name.toLowerCase().includes(q) || (s.nif || "").toLowerCase().includes(q) || (s.email || "").toLowerCase().includes(q)
    );

    return {
        suppliers, loading, search, setSearch,
        showModal, setShowModal,
        editingId, form, setForm,
        saving, deletingId,
        openNew, openEdit, handleSubmit, handleDelete,
        filtered,
    };
}
