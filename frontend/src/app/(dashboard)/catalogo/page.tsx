"use client";

import { useEffect, useState } from "react";
import { api, Product } from "@/lib/api";
import { Package, Plus, Pencil, Trash2, Loader2, DollarSign, X } from "lucide-react";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";
import { ColumnDef } from "@tanstack/react-table";
import { DataTable, DataTableColumnHeader } from "@/components/data-table";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";

type FormState = {
    name: string; sku: string; description: string;
    price: string; tax_percentage: string; item_type: string;
};

const emptyForm = (): FormState => ({
    name: "", sku: "", description: "", price: "", tax_percentage: "21", item_type: "product"
});

const fmt = (val: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(val);

export default function CatalogPage() {
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

    const columns: ColumnDef<Product, any>[] = [
        {
            accessorKey: "sku",
            header: ({ column }) => <DataTableColumnHeader column={column} title="SKU" />,
            cell: ({ row }) => (
                <span className="font-mono text-xs text-muted-foreground">{row.getValue("sku") || "—"}</span>
            ),
        },
        {
            accessorKey: "name",
            header: ({ column }) => <DataTableColumnHeader column={column} title="Nombre" />,
            cell: ({ row }) => {
                const prod = row.original;
                return (
                    <div>
                        <span className="font-medium text-foreground">{prod.name}</span>
                        {prod.description && (
                            <span className="block text-xs text-muted-foreground truncate max-w-xs">{prod.description}</span>
                        )}
                    </div>
                );
            },
        },
        {
            accessorKey: "item_type",
            header: ({ column }) => <DataTableColumnHeader column={column} title="Tipo" />,
            cell: ({ row }) => <StatusBadge status={row.getValue("item_type")} />,
            filterFn: (row, id, value) => value.includes(row.getValue(id)),
        },
        {
            accessorKey: "price",
            header: ({ column }) => <DataTableColumnHeader column={column} title="Precio base" />,
            cell: ({ row }) => {
                const prod = row.original;
                return (
                    <div className="text-right">
                        <span className="font-medium text-foreground tabular-nums">{fmt(prod.price)}</span>
                        <span className="text-[10px] text-muted-foreground block">+{prod.tax_percentage}% IVA</span>
                    </div>
                );
            },
        },
        {
            id: "pvp",
            accessorFn: (row) => row.price * (1 + row.tax_percentage / 100),
            header: ({ column }) => <DataTableColumnHeader column={column} title="PVP (c/ IVA)" />,
            cell: ({ row }) => {
                const pvp = row.original.price * (1 + row.original.tax_percentage / 100);
                return <span className="font-semibold text-right tabular-nums text-primary">{fmt(pvp)}</span>;
            },
        },
        {
            id: "actions",
            cell: ({ row }) => {
                const prod = row.original;
                return (
                    <div className="flex items-center justify-end gap-1">
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => openEdit(prod)}
                            title="Editar"
                        >
                            <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-destructive hover:text-destructive"
                            onClick={() => handleDelete(prod.id, prod.name)}
                            disabled={deletingId === prod.id}
                            title="Eliminar"
                        >
                            {deletingId === prod.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                        </Button>
                    </div>
                );
            },
        },
    ];

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Catálogo de Artículos"
                description="Gestiona productos y servicios. La IA los usa para emitir facturas y presupuestos."
                icon={Package}
                actions={
                    <Button onClick={openCreate}>
                        <Plus className="mr-2 h-4 w-4" />Nuevo Artículo
                    </Button>
                }
            />

            {!isLoading && products.length === 0 ? (
                <EmptyState
                    icon={Package}
                    title="Tu catálogo está vacío"
                    description="Añade productos y servicios para que la IA pueda generar facturas y presupuestos automáticamente."
                    action={
                        <Button onClick={openCreate}>
                            <Plus className="mr-2 h-4 w-4" />Nuevo Artículo
                        </Button>
                    }
                />
            ) : (
                <DataTable
                    columns={columns}
                    data={products}
                    isLoading={isLoading}
                    searchKey="name"
                    searchPlaceholder="Buscar por nombre..."
                    emptyMessage="Sin artículos encontrados."
                />
            )}

            {/* Modal crear/editar */}
            {showModal && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-card border border-border rounded-2xl w-full max-w-xl overflow-hidden shadow-2xl">
                        <div className="p-5 border-b border-border flex justify-between items-center bg-muted">
                            <h2 className="text-lg font-medium text-foreground flex items-center gap-2">
                                <Package className="w-4 h-4 text-primary" />
                                {editingId ? "Editar Artículo" : "Nuevo Artículo"}
                            </h2>
                            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setShowModal(false)}>
                                <X className="h-5 w-5" />
                            </Button>
                        </div>

                        <form onSubmit={handleSubmit} className="p-6 space-y-5">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm text-muted-foreground mb-1.5">Nombre *</label>
                                    <input
                                        type="text"
                                        required
                                        value={form.name}
                                        onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                                        className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary transition-colors"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm text-muted-foreground mb-1.5">SKU / Ref.</label>
                                    <input
                                        type="text"
                                        value={form.sku}
                                        onChange={e => setForm(f => ({ ...f, sku: e.target.value }))}
                                        placeholder="Opcional"
                                        className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary font-mono text-sm transition-colors"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm text-muted-foreground mb-1.5">Descripción</label>
                                <textarea
                                    value={form.description}
                                    onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                                    className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary resize-none h-20 transition-colors"
                                />
                            </div>
                            <div className="grid grid-cols-3 gap-4 border-t border-border pt-4">
                                <div>
                                    <label className="block text-sm text-muted-foreground mb-1.5">Naturaleza</label>
                                    <select
                                        value={form.item_type}
                                        onChange={e => setForm(f => ({ ...f, item_type: e.target.value }))}
                                        className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-primary transition-colors"
                                    >
                                        <option value="product">Producto</option>
                                        <option value="service">Servicio</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm text-muted-foreground mb-1.5">Precio Base (*) *</label>
                                    <div className="relative">
                                        <DollarSign className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                                        <input
                                            type="number"
                                            required
                                            min="0"
                                            step="0.01"
                                            value={form.price}
                                            onChange={e => setForm(f => ({ ...f, price: e.target.value }))}
                                            className="w-full bg-background border border-border rounded-lg pl-9 pr-3 py-2 text-foreground focus:outline-none focus:border-primary transition-colors"
                                        />
                                    </div>
                                </div>
                                <div>
                                    <label className="block text-sm text-muted-foreground mb-1.5">% IVA</label>
                                    <select
                                        value={form.tax_percentage}
                                        onChange={e => setForm(f => ({ ...f, tax_percentage: e.target.value }))}
                                        className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-primary transition-colors"
                                    >
                                        <option value="21">21%</option>
                                        <option value="10">10% (reducido)</option>
                                        <option value="4">4% (superreducido)</option>
                                        <option value="0">0% (exento)</option>
                                    </select>
                                </div>
                            </div>
                            <div className="pt-4 flex justify-end gap-3">
                                <Button type="button" variant="outline" onClick={() => setShowModal(false)}>
                                    Cancelar
                                </Button>
                                <Button type="submit" disabled={isSubmitting || !form.name || !form.price}>
                                    {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                    {editingId ? "Guardar cambios" : "Crear artículo"}
                                </Button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
