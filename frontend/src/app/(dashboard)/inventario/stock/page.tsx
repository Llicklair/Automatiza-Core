"use client";

import { useEffect, useRef, useState } from "react";
import { Package, Plus, AlertTriangle, Pencil, Trash2, MoreHorizontal, ChevronDown, ChevronUp, Search, X, Warehouse as WarehouseIcon, ShoppingCart, Tags, BarChart3, PackageMinus } from "lucide-react";
import { useTranslations } from "next-intl";
import { ColumnDef } from "@tanstack/react-table";
import { type Product } from "@/lib/api";
import { DataTable, DataTableColumnHeader } from "@/components/data-table";
import { PageHeader } from "@/components/shared/PageHeader";
import { KpiCard } from "@/components/shared/KpiCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useStock } from "./_hooks/useStock";
import { StockStatus, MovementsPanel } from "./_components/StockHelpers";
import { MovementModal } from "./_components/MovementModal";
import { ProductModal } from "./_components/ProductModal";
import { LotsPanel } from "./_components/LotsPanel";
import { ExpiringLotsPanel } from "./_components/ExpiringLotsPanel";
import { WarehouseStockPanel } from "./_components/WarehouseStockPanel";
import Link from "next/link";

const fmt = (n: number) => n.toLocaleString("es-ES");

export default function StockPage() {
    const t = useTranslations("inventario");
    const tc = useTranslations("common");
    const {
        products, loading, expandedId, movements, movementsLoading,
        showModal, setShowModal, selectedProduct,
        movForm, setMovForm, saving,
        showProductModal, setShowProductModal, editingProduct,
        productForm, setProductForm, savingProduct,
        editingAlertId, setEditingAlertId, alertValue, setAlertValue,
        alertInputRef,
        query, setQuery, categoryFilter, setCategoryFilter,
        handleMovement, handleProductSubmit, handleDelete,
        toggleExpand, openMovement, openCreateProduct, openEditProduct,
        startEditAlert, saveAlert,
    } = useStock();

    const seenCategoriesRef = useRef<Set<string>>(new Set());
    const [categoryList, setCategoryList] = useState<string[]>([]);
    useEffect(() => {
        let changed = false;
        for (const p of products) {
            if (p.category && !seenCategoriesRef.current.has(p.category)) {
                seenCategoriesRef.current.add(p.category);
                changed = true;
            }
        }
        if (changed) setCategoryList(Array.from(seenCategoriesRef.current).sort());
    }, [products]);
    const hasFilters = query.length > 0 || categoryFilter.length > 0;

    const totalStock = products.reduce((acc, p) => acc + (p.stock_quantity || 0), 0);
    const lowStock = products.filter(p => p.stock_min_alert > 0 && p.stock_quantity <= p.stock_min_alert).length;
    const outOfStock = products.filter(p => p.stock_quantity === 0).length;

    const columns: ColumnDef<Product, any>[] = [
        {
            accessorKey: "name",
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("stock.colProduct")} />,
            cell: ({ row }) => {
                const product = row.original;
                return (
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center flex-shrink-0">
                            <Package className="w-4 h-4 text-muted-foreground" />
                        </div>
                        <div>
                            <p className="text-sm font-medium text-foreground">{product.name}</p>
                            {product.sku && <p className="text-xs text-muted-foreground font-mono">{product.sku}</p>}
                        </div>
                    </div>
                );
            },
        },
        {
            accessorKey: "location",
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("stock.colLocation")} />,
            cell: ({ row }) => (
                row.original.location
                    ? <span className="text-sm text-foreground">{row.original.location}</span>
                    : <span className="text-xs text-muted-foreground italic">—</span>
            ),
        },
        {
            accessorKey: "stock_quantity",
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("stock.colCurrentStock")} />,
            cell: ({ row }) => {
                const product = row.original;
                const isOut = product.stock_quantity === 0;
                const isLow = product.stock_min_alert > 0 && product.stock_quantity <= product.stock_min_alert;
                return (
                    <div className="flex flex-col">
                        <span className={`text-lg font-bold font-mono ${isOut ? "text-rose-400" : isLow ? "text-amber-400" : "text-foreground"}`}>
                            {t("stock.unitsShort", { value: fmt(product.stock_quantity) })}
                        </span>
                        <span className="text-xs text-muted-foreground font-mono">
                            {t("stock.boxesShort", { value: fmt(product.stock_boxes) })}
                        </span>
                    </div>
                );
            },
        },
        {
            accessorKey: "stock_min_alert",
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("stock.colMinAlert")} />,
            cell: ({ row }) => {
                const product = row.original;
                if (editingAlertId === product.id) {
                    return (
                        <form
                            onSubmit={e => { e.preventDefault(); saveAlert(product.id); }}
                            className="flex items-center gap-1"
                        >
                            <input
                                ref={alertInputRef}
                                type="number"
                                min={0}
                                value={alertValue}
                                onChange={e => setAlertValue(parseInt(e.target.value) || 0)}
                                onBlur={() => saveAlert(product.id)}
                                onKeyDown={e => { if (e.key === "Escape") setEditingAlertId(null); }}
                                className="w-16 bg-card border border-primary text-foreground text-sm rounded-lg px-2 py-1 text-center focus:outline-none"
                            />
                        </form>
                    );
                }
                return (
                    <div className="flex items-center gap-1.5">
                        <span className="text-sm text-muted-foreground font-mono">
                            {product.stock_min_alert > 0 ? fmt(product.stock_min_alert) : "—"}
                        </span>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6"
                            onClick={() => startEditAlert(product)}
                            title={t("stock.editMinAlert")}
                         aria-label={t("stock.editMinAlert")}>
                            <Pencil className="w-3 h-3" aria-hidden="true" />
                        </Button>
                    </div>
                );
            },
        },
        {
            id: "status",
            header: ({ column }) => <DataTableColumnHeader column={column} title={t("stock.colStatus")} />,
            accessorFn: (row) => {
                if (row.stock_quantity === 0) return "out_of_stock";
                if (row.stock_min_alert > 0 && row.stock_quantity <= row.stock_min_alert) return "low_stock";
                return "ok";
            },
            cell: ({ row }) => <StockStatus product={row.original} />,
            filterFn: (row, id, value) => value.includes(row.getValue(id)),
        },
        {
            id: "actions",
            cell: ({ row }) => {
                const product = row.original;
                const isExpanded = expandedId === product.id;
                return (
                    <div className="flex items-center justify-end gap-1">
                        <Button
                            variant="default"
                            size="sm"
                            onClick={() => openMovement(product)}
                            className="h-7 text-xs"
                        >
                            <Plus className="mr-1 w-3 h-3" /> {t("stock.movement")}
                        </Button>
                        <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon" className="h-8 w-8" aria-label={t("stock.openActionsMenu")}>
                                    <MoreHorizontal className="w-4 h-4" aria-hidden="true" />
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                                <DropdownMenuItem onClick={() => openEditProduct(product)}>
                                    <Pencil className="mr-2 w-3.5 h-3.5" /> {tc("edit")}
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => openMovement(product, "salida")}>
                                    <PackageMinus className="mr-2 w-3.5 h-3.5" /> {t("stock.writeOff")}
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                    onClick={() => handleDelete(product)}
                                    className="text-destructive focus:text-destructive"
                                >
                                    <Trash2 className="mr-2 w-3.5 h-3.5" /> {tc("delete")}
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => toggleExpand(product.id)}
                            title={t("stock.expandDetails")}
                         aria-label={t("stock.expandDetails")}>
                            {isExpanded ? <ChevronUp className="w-4 h-4" aria-hidden="true" /> : <ChevronDown className="w-4 h-4" aria-hidden="true" />}
                        </Button>
                    </div>
                );
            },
        },
    ];

    const statusFilterOptions = [
        { label: t("stock.statusOk"), value: "ok" },
        { label: t("stock.statusLow"), value: "low_stock" },
        { label: t("stock.statusOut"), value: "out_of_stock" },
    ];

    const newProductButton = (
        <Button onClick={openCreateProduct}>
            <Plus className="mr-2 h-4 w-4" /> {t("stock.newProduct")}
        </Button>
    );

    const headerActions = (
        <div className="flex items-center gap-2">
            <Link href="/inventario/analitica">
                <Button variant="outline">
                    <BarChart3 className="mr-2 h-4 w-4" /> {t("stock.navAnalytics")}
                </Button>
            </Link>
            <Link href="/inventario/etiquetas">
                <Button variant="outline">
                    <Tags className="mr-2 h-4 w-4" /> {t("stock.navLabels")}
                </Button>
            </Link>
            <Link href="/inventario/reposicion">
                <Button variant="outline">
                    <ShoppingCart className="mr-2 h-4 w-4" /> {t("stock.navReorder")}
                </Button>
            </Link>
            <Link href="/inventario/almacenes">
                <Button variant="outline">
                    <WarehouseIcon className="mr-2 h-4 w-4" /> {t("stock.navWarehouses")}
                </Button>
            </Link>
            {newProductButton}
        </div>
    );

    if (!loading && products.length === 0) {
        return (
            <div className="p-6 space-y-6">
                <PageHeader
                    title={t("stock.title")}
                    description={t("stock.description")}
                    icon={Package}
                    actions={headerActions}
                />
                <EmptyState
                    icon={Package}
                    title={t("stock.emptyTitle")}
                    description={t("stock.emptyDescription")}
                    action={{ label: t("stock.newProduct"), onClick: openCreateProduct }}
                />
                <ProductModal
                    open={showProductModal}
                    onOpenChange={setShowProductModal}
                    editingProduct={editingProduct}
                    productForm={productForm}
                    setProductForm={setProductForm}
                    onSubmit={handleProductSubmit}
                    saving={savingProduct}
                />
            </div>
        );
    }

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title={t("stock.title")}
                description={t("stock.description")}
                icon={Package}
                actions={headerActions}
            />

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <KpiCard title={t("stock.kpiUnitsInStock")} value={fmt(totalStock)} icon={Package} />
                <KpiCard
                    title={t("stock.kpiLowStock")}
                    value={t("stock.productsCount", { count: lowStock })}
                    icon={AlertTriangle}
                    className={lowStock > 0 ? "border-amber-500/20" : ""}
                />
                <KpiCard
                    title={t("stock.kpiOutOfStock")}
                    value={t("stock.productsCount", { count: outOfStock })}
                    icon={AlertTriangle}
                    className={outOfStock > 0 ? "border-rose-500/20" : ""}
                />
            </div>

            <ExpiringLotsPanel />

            <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center">
                <div className="relative flex-1 max-w-md">
                    <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                    <Input
                        type="text"
                        value={query}
                        onChange={e => setQuery(e.target.value)}
                        placeholder={t("stock.searchPlaceholder")}
                        className="pl-9 pr-9"
                    />
                    {query && (
                        <button
                            type="button"
                            onClick={() => setQuery("")}
                            className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground"
                            aria-label={t("stock.clearSearch")}
                        >
                            <X className="w-3.5 h-3.5" />
                        </button>
                    )}
                </div>
                <select
                    value={categoryFilter}
                    onChange={e => setCategoryFilter(e.target.value)}
                    className="bg-background border border-border text-foreground text-sm rounded-md px-3 py-2 h-9 focus:outline-none focus:ring-2 focus:ring-ring transition-colors min-w-[180px]"
                    aria-label={t("stock.filterByCategory")}
                >
                    <option value="">{t("stock.allCategories")}</option>
                    {categoryList.map(c => (
                        <option key={c} value={c}>{c}</option>
                    ))}
                </select>
                {hasFilters && (
                    <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => { setQuery(""); setCategoryFilter(""); }}
                        className="text-xs"
                    >
                        {t("stock.clearFilters")}
                    </Button>
                )}
            </div>

            <DataTable
                columns={columns}
                data={products}
                isLoading={loading}
                facetedFilters={[{ column: "status", title: t("stock.colStatus"), options: statusFilterOptions }]}
                emptyMessage={t("stock.noProductsFound")}
                pageSize={20}
            />

            {expandedId && (
                <div className="space-y-4">
                    <MovementsPanel
                        productId={expandedId}
                        movements={movements}
                        movementsLoading={movementsLoading}
                    />
                    <LotsPanel productId={expandedId} />
                    <WarehouseStockPanel productId={expandedId} />
                </div>
            )}

            <MovementModal
                open={showModal}
                onOpenChange={setShowModal}
                selectedProduct={selectedProduct}
                movForm={movForm}
                setMovForm={setMovForm}
                onSubmit={handleMovement}
                saving={saving}
            />

            <ProductModal
                open={showProductModal}
                onOpenChange={setShowProductModal}
                editingProduct={editingProduct}
                productForm={productForm}
                setProductForm={setProductForm}
                onSubmit={handleProductSubmit}
                saving={savingProduct}
            />
        </div>
    );
}
