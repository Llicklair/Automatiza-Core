"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
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
import { PageContainer } from "@/components/shared/PageContainer";

const fmt = (val: number) =>
    new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(val);

export default function CatalogPage() {
    const t = useTranslations("catalogo");
    const tc = useTranslations("common");
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
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("columns.name")} />,
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
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("columns.type")} />,
            cell: ({ row }) => <StatusBadge status={row.getValue("item_type")} />,
            filterFn: (row, id, value) => value.includes(row.getValue(id)),
        },
        {
            accessorKey: "price",
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("columns.basePrice")} />,
            cell: ({ row }) => {
                const prod = row.original;
                return (
                    <div className="text-right">
                        <span className="font-medium text-foreground tabular-nums">{fmt(prod.price)}</span>
                        <span className="text-[10px] text-muted-foreground block">{t("columns.vatSuffix", { pct: prod.tax_percentage })}</span>
                    </div>
                );
            },
        },
        {
            id: "pvp",
            accessorFn: (row) => row.price * (1 + row.tax_percentage / 100),
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("columns.pvp")} />,
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
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => openEdit(prod)} title={tc("edit")} aria-label={tc("edit")}>
                            <Pencil className="h-4 w-4" aria-hidden="true" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-destructive hover:text-destructive"
                            onClick={() => handleDelete(prod.id, prod.name)}
                            disabled={deletingId === prod.id}
                            title={tc("delete")}
                         aria-label={tc("delete")}>
                            {deletingId === prod.id ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Trash2 className="h-4 w-4" aria-hidden="true" />}
                        </Button>
                    </div>
                );
            },
        },
    ];

    return (
        <PageContainer width="full">
            <PageHeader
                title={t("header.title")}
                description={t("header.description")}
                icon={Package}
                actions={
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => setShowImport(true)}>
                            <Upload className="mr-2 h-4 w-4" /> {t("header.importCsv")}
                        </Button>
                        <Button onClick={openCreate}>
                            <Plus className="mr-2 h-4 w-4" />{t("header.newItem")}
                        </Button>
                    </div>
                }
            />

            {!isLoading && products.length === 0 ? (
                <EmptyState
                    icon={Package}
                    title={t("empty.title")}
                    description={t("empty.description")}
                    action={{ label: t("header.newItem"), onClick: openCreate }}
                />
            ) : (
                <DataTable
                    columns={columns}
                    data={products}
                    isLoading={isLoading}
                    searchKey="name"
                    searchPlaceholder={t("table.searchPlaceholder")}
                    emptyMessage={t("table.empty")}
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
                entityName={t("import.entityName")}
                columns={[
                    { header: t("import.cols.name"), field: "nombre", required: true, example: t("import.examples.name") },
                    { header: "SKU", field: "sku", example: "SRV-001" },
                    { header: t("import.cols.description"), field: "descripcion", example: t("import.examples.description") },
                    { header: t("import.cols.price"), field: "precio", required: true, example: "150.00" },
                    { header: t("import.cols.vat"), field: "iva", example: "21" },
                    { header: t("import.cols.stock"), field: "stock", example: "0" },
                ]}
                onImport={(rows) => api.importBulk.products(rows)}
                onSuccess={() => window.location.reload()}
            />
        </PageContainer>
    );
}
