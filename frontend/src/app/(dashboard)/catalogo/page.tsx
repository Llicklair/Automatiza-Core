"use client";

import { useState } from "react";
import { Package, Plus, Pencil, Trash2, Loader2, Upload } from "lucide-react";
import { ColumnDef } from "@tanstack/react-table";
import { Product } from "@/lib/api";
import { DataTable, DataTableColumnHeader } from "@/components/data-table";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/button";
import { useCatalogPage } from "./_hooks/useCatalogPage";
import { ProductModal } from "./_components/ProductModal";
import { ImportCsvModal } from "@/components/shared/ImportCsvModal";
import { api } from "@/lib/api";

const fmt = (val: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(val);

export default function CatalogPage() {
    const {
        products, isLoading,
        showModal, setShowModal,
        editingId, form, setForm,
        isSubmitting, deletingId,
        openCreate, openEdit, handleSubmit, handleDelete,
    } = useCatalogPage();

    const [showImport, setShowImport] = useState(false);

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
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => openEdit(prod)} title="Editar">
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
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => setShowImport(true)}>
                            <Upload className="mr-2 h-4 w-4" /> Importar CSV
                        </Button>
                        <Button onClick={openCreate}>
                            <Plus className="mr-2 h-4 w-4" />Nuevo Artículo
                        </Button>
                    </div>
                }
            />

            {!isLoading && products.length === 0 ? (
                <EmptyState
                    icon={Package}
                    title="Tu catálogo está vacío"
                    description="Añade productos y servicios para que la IA pueda generar facturas y presupuestos automáticamente."
                    action={{ label: "Nuevo Artículo", onClick: openCreate }}
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

            {showModal && (
                <ProductModal
                    editingId={editingId}
                    form={form}
                    onChange={setForm}
                    onSubmit={handleSubmit}
                    onClose={() => setShowModal(false)}
                    isSubmitting={isSubmitting}
                />
            )}

            <ImportCsvModal
                open={showImport}
                onClose={() => setShowImport(false)}
                entityName="productos"
                columns={[
                    { header: "Nombre", field: "nombre", required: true, example: "Servicio de consultoría" },
                    { header: "SKU", field: "sku", example: "SRV-001" },
                    { header: "Descripción", field: "descripcion", example: "Consultoría hora" },
                    { header: "Precio", field: "precio", required: true, example: "150.00" },
                    { header: "IVA %", field: "iva", example: "21" },
                    { header: "Stock", field: "stock", example: "0" },
                ]}
                onImport={(rows) => api.importBulk.products(rows)}
                onSuccess={() => window.location.reload()}
            />
        </div>
    );
}
