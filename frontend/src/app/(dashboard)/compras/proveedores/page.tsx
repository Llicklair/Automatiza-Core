"use client";

import { useEffect, useState } from "react";
import { api, type Client } from "@/lib/api";
import { Truck, Plus, Search, Pencil, Trash2, Loader2, X, Building2, Mail, MapPin, Hash } from "lucide-react";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";

const EMPTY_FORM = { name: "", nif: "", email: "", address: "", city: "", postal_code: "" };

export default function ProveedoresPage() {
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

    return (
        <div className="p-8 max-w-6xl mx-auto space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-foreground tracking-tight">Proveedores</h1>
                    <p className="mt-1 text-sm text-muted-foreground">Gestiona el directorio de proveedores y sus datos de contacto.</p>
                </div>
                <button
                    onClick={openNew}
                    className="flex items-center gap-2 bg-primary hover:bg-primary text-foreground text-sm font-medium px-4 py-2.5 rounded-xl transition-colors"
                >
                    <Plus className="w-4 h-4" /> Nuevo proveedor
                </button>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-4">
                {[
                    { label: "Total proveedores", value: suppliers.length, color: "text-foreground" },
                    { label: "Con email", value: suppliers.filter(s => s.email).length, color: "text-primary" },
                    { label: "Con NIF/CIF", value: suppliers.filter(s => s.nif).length, color: "text-emerald-400" },
                ].map(stat => (
                    <div key={stat.label} className="bg-card border border-border rounded-2xl p-5">
                        <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">{stat.label}</p>
                        <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
                    </div>
                ))}
            </div>

            {/* Search */}
            <div className="relative">
                <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                    type="text"
                    placeholder="Buscar por nombre, NIF o email..."
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    className="w-full bg-card border border-border text-foreground text-sm rounded-xl pl-9 pr-4 py-2.5 focus:outline-none focus:border-primary transition-colors"
                />
            </div>

            {/* Table */}
            {loading ? (
                <div className="flex items-center justify-center py-24 text-muted-foreground gap-2">
                    <Loader2 className="w-5 h-5 animate-spin" /> Cargando proveedores…
                </div>
            ) : filtered.length === 0 ? (
                <div className="bg-card border border-border rounded-2xl p-16 flex flex-col items-center text-center">
                    <Truck className="w-12 h-12 text-muted-foreground mb-4" />
                    <h2 className="text-lg font-bold text-foreground mb-2">
                        {suppliers.length === 0 ? "Sin proveedores" : "Sin resultados"}
                    </h2>
                    <p className="text-sm text-muted-foreground max-w-md">
                        {suppliers.length === 0
                            ? "Añade tu primer proveedor para gestionar compras y pagos."
                            : `No hay proveedores que coincidan con "${search}"`}
                    </p>
                    {suppliers.length === 0 && (
                        <button onClick={openNew} className="mt-6 bg-primary hover:bg-primary text-foreground text-sm px-4 py-2 rounded-xl transition-colors">
                            Añadir proveedor
                        </button>
                    )}
                </div>
            ) : (
                <div className="bg-card border border-border rounded-2xl overflow-hidden">
                    <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-border text-xs font-medium text-muted-foreground uppercase tracking-wide bg-muted">
                        <div className="col-span-4">Proveedor</div>
                        <div className="col-span-2">NIF/CIF</div>
                        <div className="col-span-3">Email</div>
                        <div className="col-span-2">Ciudad</div>
                        <div className="col-span-1 text-right">Acciones</div>
                    </div>
                    {filtered.map(s => (
                        <div key={s.id} className="grid grid-cols-12 gap-4 px-6 py-3.5 border-b border-border/50 last:border-0 hover:bg-accent/50 transition-colors items-center">
                            <div className="col-span-4 flex items-center gap-3">
                                <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
                                    <Building2 className="w-4 h-4 text-primary" />
                                </div>
                                <span className="text-sm font-medium text-foreground truncate">{s.name}</span>
                            </div>
                            <div className="col-span-2">
                                <span className="text-sm text-muted-foreground font-mono">{s.nif || <span className="text-muted-foreground italic">—</span>}</span>
                            </div>
                            <div className="col-span-3">
                                {s.email ? (
                                    <span className="text-sm text-muted-foreground truncate flex items-center gap-1">
                                        <Mail className="w-3 h-3 text-muted-foreground" /> {s.email}
                                    </span>
                                ) : <span className="text-muted-foreground italic text-sm">—</span>}
                            </div>
                            <div className="col-span-2">
                                {s.city ? (
                                    <span className="text-sm text-muted-foreground flex items-center gap-1">
                                        <MapPin className="w-3 h-3 text-muted-foreground" /> {s.city}
                                    </span>
                                ) : <span className="text-muted-foreground italic text-sm">—</span>}
                            </div>
                            <div className="col-span-1 flex items-center justify-end gap-1">
                                <button onClick={() => openEdit(s)} className="p-1.5 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors">
                                    <Pencil className="w-3.5 h-3.5" />
                                </button>
                                <button
                                    onClick={() => handleDelete(s.id)}
                                    disabled={deletingId === s.id}
                                    className="p-1.5 rounded-lg hover:bg-rose-500/10 text-muted-foreground hover:text-rose-400 transition-colors"
                                >
                                    {deletingId === s.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Modal */}
            {showModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
                    <div className="bg-card border border-border rounded-2xl p-8 w-full max-w-lg shadow-2xl">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-lg font-bold text-foreground">{editingId ? "Editar proveedor" : "Nuevo proveedor"}</h2>
                            <button onClick={() => setShowModal(false)} className="text-muted-foreground hover:text-foreground transition-colors">
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="col-span-2">
                                    <label className="block text-xs text-muted-foreground mb-1.5 font-medium">Nombre / Razón social *</label>
                                    <input
                                        type="text" required value={form.name}
                                        onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                                        className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors"
                                        placeholder="Proveedor S.L."
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs text-muted-foreground mb-1.5 font-medium">NIF / CIF</label>
                                    <input
                                        type="text" value={form.nif}
                                        onChange={e => setForm(f => ({ ...f, nif: e.target.value }))}
                                        className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors"
                                        placeholder="B12345678"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs text-muted-foreground mb-1.5 font-medium">Email</label>
                                    <input
                                        type="email" value={form.email}
                                        onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                                        className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors"
                                        placeholder="proveedor@empresa.com"
                                    />
                                </div>
                                <div className="col-span-2">
                                    <label className="block text-xs text-muted-foreground mb-1.5 font-medium">Dirección</label>
                                    <input
                                        type="text" value={form.address}
                                        onChange={e => setForm(f => ({ ...f, address: e.target.value }))}
                                        className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors"
                                        placeholder="Calle Mayor, 1"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs text-muted-foreground mb-1.5 font-medium">Ciudad</label>
                                    <input
                                        type="text" value={form.city}
                                        onChange={e => setForm(f => ({ ...f, city: e.target.value }))}
                                        className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors"
                                        placeholder="Madrid"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs text-muted-foreground mb-1.5 font-medium">Código postal</label>
                                    <input
                                        type="text" value={form.postal_code}
                                        onChange={e => setForm(f => ({ ...f, postal_code: e.target.value }))}
                                        className="w-full bg-card border border-border text-foreground text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-primary transition-colors"
                                        placeholder="28001"
                                    />
                                </div>
                            </div>
                            <div className="flex gap-3 pt-2">
                                <button type="button" onClick={() => setShowModal(false)} className="flex-1 py-2.5 rounded-xl border border-border text-muted-foreground text-sm hover:bg-accent/50 transition-colors">
                                    Cancelar
                                </button>
                                <button type="submit" disabled={saving} className="flex-1 py-2.5 rounded-xl bg-primary hover:bg-primary text-foreground text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2">
                                    {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                                    {editingId ? "Guardar cambios" : "Crear proveedor"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
