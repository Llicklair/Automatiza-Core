"use client";

import { Truck, Plus, Search, Pencil, Trash2, Loader2, Building2, Mail, MapPin } from "lucide-react";
import { useProveedores } from "./_hooks/useProveedores";
import { ProveedorModal } from "./_components/ProveedorModal";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function ProveedoresPage() {
    const {
        suppliers, loading, search, setSearch,
        showModal, setShowModal,
        editingId, form, setForm,
        saving, deletingId,
        openNew, openEdit, handleSubmit, handleDelete,
        filtered,
    } = useProveedores();

    return (
        <div className="p-8 max-w-[1400px] mx-auto space-y-6">
            <PageHeader
                title="Proveedores"
                description="Gestiona el directorio de proveedores y sus datos de contacto."
                icon={Truck}
                actions={
                    <Button onClick={openNew}>
                        <Plus className="w-4 h-4 mr-2" /> Nuevo proveedor
                    </Button>
                }
            />

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

            <div className="relative">
                <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                <Input
                    placeholder="Buscar por nombre, NIF o email..."
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    className="pl-9"
                />
            </div>

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
                        <Button onClick={openNew} className="mt-6">Añadir proveedor</Button>
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
                                <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-foreground" onClick={() => openEdit(s)} aria-label="Editar proveedor">
                                    <Pencil className="w-3.5 h-3.5" aria-hidden="true" />
                                </Button>
                                <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-rose-400 hover:bg-rose-500/10" onClick={() => handleDelete(s.id)} disabled={deletingId === s.id} aria-label="Eliminar proveedor">
                                    {deletingId === s.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" /> : <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />}
                                </Button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {showModal && (
                <ProveedorModal
                    editingId={editingId}
                    form={form}
                    setForm={setForm}
                    saving={saving}
                    onClose={() => setShowModal(false)}
                    onSubmit={handleSubmit}
                />
            )}
        </div>
    );
}
