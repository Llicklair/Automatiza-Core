"use client";

import { useEffect, useState, useRef } from "react";
import { api, type Product, type StockMovement } from "@/lib/api";
import {
    Package, Plus, ArrowUpCircle, ArrowDownCircle, SlidersHorizontal,
    Loader2, X, AlertTriangle, ChevronDown, ChevronUp, Clock, Pencil, Trash2, MoreHorizontal
} from "lucide-react";
import { useToastStore } from "@/stores/toast";
import { useConfirmStore } from "@/stores/confirm";
import { logError } from "@/lib/logger";
import { ColumnDef } from "@tanstack/react-table";
import { DataTable, DataTableColumnHeader } from "@/components/data-table";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { KpiCard } from "@/components/shared/KpiCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const fmt = (n: number) => n.toLocaleString("es-ES");

const MOVEMENT_ICONS: Record<string, React.ReactNode> = {
    entrada: <ArrowUpCircle className="w-4 h-4 text-emerald-400" />,
    salida: <ArrowDownCircle className="w-4 h-4 text-rose-400" />,
    ajuste: <SlidersHorizontal className="w-4 h-4 text-amber-400" />,
};

const MOVEMENT_COLORS: Record<string, string> = {
    entrada: "text-emerald-400",
    salida: "text-rose-400",
    ajuste: "text-amber-400",
};

interface MovementForm {
    movement_type: "entrada" | "salida" | "ajuste";
    quantity: number;
    reference: string;
    notes: string;
}

interface ProductForm {
    name: string;
    sku: string;
    price: number;
    stock_min_alert: number;
    description: string;
}

const emptyProductForm: ProductForm = { name: "", sku: "", price: 0, stock_min_alert: 0, description: "" };

// --- Stock status helper for StatusBadge ---
function StockStatus({ product }: { product: Product }) {
    const isOut = product.stock_quantity === 0;
    const isLow = product.stock_min_alert > 0 && product.stock_quantity <= product.stock_min_alert;
    if (isOut) return <StatusBadge status="out_of_stock" label="Sin stock" />;
    if (isLow) return <StatusBadge status="low_stock" label="Stock bajo" />;
    return <StatusBadge status="active" label="OK" />;
}

// --- Movements panel (expanded row) ---
function MovementsPanel({ productId, movements, movementsLoading }: {
    productId: string;
    movements: Record<string, StockMovement[]>;
    movementsLoading: string | null;
}) {
    return (
        <Card className="mx-4 mb-4 mt-1">
            <CardContent className="p-4">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Historial de movimientos</p>
                {movementsLoading === productId ? (
                    <div className="flex items-center gap-2 text-muted-foreground text-sm py-2">
                        <Loader2 className="w-4 h-4 animate-spin" /> Cargando...
                    </div>
                ) : !movements[productId] || movements[productId].length === 0 ? (
                    <p className="text-muted-foreground text-sm italic">Sin movimientos registrados.</p>
                ) : (
                    <div className="space-y-2">
                        {movements[productId].slice(0, 10).map(mov => (
                            <div key={mov.id} className="flex items-center gap-3 text-sm">
                                {MOVEMENT_ICONS[mov.movement_type]}
                                <span className={`font-medium w-14 ${MOVEMENT_COLORS[mov.movement_type]}`}>
                                    {mov.movement_type === "entrada" ? "+" : mov.movement_type === "salida" ? "-" : "="}{Math.abs(mov.quantity)}
                                </span>
                                <span className="text-muted-foreground flex-1">{mov.reference || mov.notes || <span className="italic text-muted-foreground">Sin referencia</span>}</span>
                                <span className="text-muted-foreground font-mono text-xs">&rarr; {fmt(mov.stock_after)} uds.</span>
                                <span className="text-muted-foreground text-xs flex items-center gap-1">
                                    <Clock className="w-3 h-3" />
                                    {new Date(mov.created_at).toLocaleDateString("es-ES")}
                                </span>
                            </div>
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

export default function StockPage() {
    const toast = useToastStore();
    const confirm = useConfirmStore();
    const [products, setProducts] = useState<Product[]>([]);
    const [loading, setLoading] = useState(true);
    const [expandedId, setExpandedId] = useState<string | null>(null);
    const [movements, setMovements] = useState<Record<string, StockMovement[]>>({});
    const [movementsLoading, setMovementsLoading] = useState<string | null>(null);

    const [showModal, setShowModal] = useState(false);
    const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
    const [movForm, setMovForm] = useState<MovementForm>({ movement_type: "entrada", quantity: 1, reference: "", notes: "" });
    const [saving, setSaving] = useState(false);

    // Product create/edit modal
    const [showProductModal, setShowProductModal] = useState(false);
    const [editingProduct, setEditingProduct] = useState<Product | null>(null);
    const [productForm, setProductForm] = useState<ProductForm>(emptyProductForm);
    const [savingProduct, setSavingProduct] = useState(false);

    // Inline edit for stock_min_alert
    const [editingAlertId, setEditingAlertId] = useState<string | null>(null);
    const [alertValue, setAlertValue] = useState(0);
    const alertInputRef = useRef<HTMLInputElement>(null);

    const load = () =>
        api.erp.products.list({ limit: 200 })
            .then(data => setProducts(data.filter(p => p.item_type === "product")))
            .catch(err => logError("inventario/stock/page", err))
            .finally(() => setLoading(false));

    useEffect(() => { load(); }, []);

    // Focus alert input when editing
    useEffect(() => {
        if (editingAlertId && alertInputRef.current) alertInputRef.current.focus();
    }, [editingAlertId]);

    const toggleExpand = async (productId: string) => {
        if (expandedId === productId) {
            setExpandedId(null);
            return;
        }
        setExpandedId(productId);
        if (!movements[productId]) {
            setMovementsLoading(productId);
            try {
                const movs = await api.erp.stock.movements(productId);
                setMovements(prev => ({ ...prev, [productId]: movs }));
            } catch (err) {
                logError("inventario/stock/page", err);
            } finally {
                setMovementsLoading(null);
            }
        }
    };

    const openMovement = (product: Product) => {
        setSelectedProduct(product);
        setMovForm({ movement_type: "entrada", quantity: 1, reference: "", notes: "" });
        setShowModal(true);
    };

    const handleMovement = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedProduct) return;
        setSaving(true);
        try {
            await api.erp.stock.addMovement(selectedProduct.id, movForm);
            setShowModal(false);
            load();
            if (movements[selectedProduct.id]) {
                const movs = await api.erp.stock.movements(selectedProduct.id);
                setMovements(prev => ({ ...prev, [selectedProduct.id]: movs }));
            }
        } catch (err: any) {
            toast.error(err?.message || "Error al registrar movimiento");
        } finally {
            setSaving(false);
        }
    };

    // --- Inline stock_min_alert edit ---
    const startEditAlert = (product: Product) => {
        setEditingAlertId(product.id);
        setAlertValue(product.stock_min_alert);
    };

    const saveAlert = async (productId: string) => {
        setEditingAlertId(null);
        try {
            await api.erp.products.update(productId, { stock_min_alert: alertValue });
            load();
            toast.success("Alerta m\u00ednima actualizada");
        } catch (err: any) {
            toast.error(err?.message || "Error al actualizar alerta");
        }
    };

    // --- Product create/edit ---
    const openCreateProduct = () => {
        setEditingProduct(null);
        setProductForm(emptyProductForm);
        setShowProductModal(true);
    };

    const openEditProduct = (product: Product) => {
        setEditingProduct(product);
        setProductForm({
            name: product.name,
            sku: product.sku || "",
            price: product.price,
            stock_min_alert: product.stock_min_alert,
            description: product.description || "",
        });
        setShowProductModal(true);
    };

    const handleProductSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSavingProduct(true);
        try {
            if (editingProduct) {
                await api.erp.products.update(editingProduct.id, productForm);
                toast.success("Producto actualizado");
            } else {
                await api.erp.products.create({ ...productForm, item_type: "product" });
                toast.success("Producto creado");
            }
            setShowProductModal(false);
            load();
        } catch (err: any) {
            toast.error(err?.message || "Error al guardar producto");
        } finally {
            setSavingProduct(false);
        }
    };

    // --- Delete product ---
    const handleDelete = async (product: Product) => {
        const ok = await confirm.show({
            title: "Eliminar producto",
            message: `Se eliminar\u00e1 "${product.name}" permanentemente. Esta acci\u00f3n no se puede deshacer.`,
            confirmLabel: "Eliminar",
            confirmVariant: "danger",
        });
        if (!ok) return;
        try {
            await api.erp.products.delete(product.id);
            toast.success("Producto eliminado");
            load();
        } catch (err: any) {
            toast.error(err?.message || "Error al eliminar producto");
        }
    };

    const totalStock = products.reduce((acc, p) => acc + (p.stock_quantity || 0), 0);
    const lowStock = products.filter(p => p.stock_min_alert > 0 && p.stock_quantity <= p.stock_min_alert).length;
    const outOfStock = products.filter(p => p.stock_quantity === 0).length;

    // --- Column definitions ---
    const columns: ColumnDef<Product, any>[] = [
        {
            accessorKey: "name",
            header: ({ column }) => <DataTableColumnHeader column={column} title="Producto" />,
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
            accessorKey: "stock_quantity",
            header: ({ column }) => <DataTableColumnHeader column={column} title="Stock actual" />,
            cell: ({ row }) => {
                const product = row.original;
                const isOut = product.stock_quantity === 0;
                const isLow = product.stock_min_alert > 0 && product.stock_quantity <= product.stock_min_alert;
                return (
                    <span className={`text-lg font-bold font-mono ${isOut ? "text-rose-400" : isLow ? "text-amber-400" : "text-foreground"}`}>
                        {fmt(product.stock_quantity)}
                    </span>
                );
            },
        },
        {
            accessorKey: "stock_min_alert",
            header: ({ column }) => <DataTableColumnHeader column={column} title="Alerta m\u00ednima" />,
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
                            {product.stock_min_alert > 0 ? fmt(product.stock_min_alert) : "\u2014"}
                        </span>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6"
                            onClick={() => startEditAlert(product)}
                            title="Editar alerta m\u00ednima"
                        >
                            <Pencil className="w-3 h-3" />
                        </Button>
                    </div>
                );
            },
        },
        {
            id: "status",
            header: ({ column }) => <DataTableColumnHeader column={column} title="Estado" />,
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
                            <Plus className="mr-1 w-3 h-3" /> Movimiento
                        </Button>
                        <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon" className="h-8 w-8">
                                    <MoreHorizontal className="w-4 h-4" />
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                                <DropdownMenuItem onClick={() => openEditProduct(product)}>
                                    <Pencil className="mr-2 w-3.5 h-3.5" /> Editar
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                    onClick={() => handleDelete(product)}
                                    className="text-destructive focus:text-destructive"
                                >
                                    <Trash2 className="mr-2 w-3.5 h-3.5" /> Eliminar
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => toggleExpand(product.id)}
                        >
                            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </Button>
                    </div>
                );
            },
        },
    ];

    const statusFilterOptions = [
        { label: "OK", value: "ok" },
        { label: "Stock bajo", value: "low_stock" },
        { label: "Sin stock", value: "out_of_stock" },
    ];

    if (!loading && products.length === 0) {
        return (
            <div className="p-6 space-y-6">
                <PageHeader
                    title="Control de Stock"
                    description="Gestiona el inventario f\u00edsico de tus productos con entradas, salidas y ajustes."
                    icon={Package}
                    actions={
                        <Button onClick={openCreateProduct}>
                            <Plus className="mr-2 h-4 w-4" /> Nuevo producto
                        </Button>
                    }
                />
                <EmptyState
                    icon={Package}
                    title="Sin productos f\u00edsicos"
                    description="A\u00f1ade productos en el cat\u00e1logo para gestionar su stock aqu\u00ed."
                    action={
                        <Button onClick={openCreateProduct}>
                            <Plus className="mr-2 h-4 w-4" /> Nuevo producto
                        </Button>
                    }
                />
                {/* Product create modal still accessible from empty state */}
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
                title="Control de Stock"
                description="Gestiona el inventario f\u00edsico de tus productos con entradas, salidas y ajustes."
                icon={Package}
                actions={
                    <Button onClick={openCreateProduct}>
                        <Plus className="mr-2 h-4 w-4" /> Nuevo producto
                    </Button>
                }
            />

            {/* KPIs */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <KpiCard
                    title="Unidades en stock"
                    value={fmt(totalStock)}
                    icon={Package}
                />
                <KpiCard
                    title="Stock bajo"
                    value={`${lowStock} productos`}
                    icon={AlertTriangle}
                    className={lowStock > 0 ? "border-amber-500/20" : ""}
                />
                <KpiCard
                    title="Sin stock"
                    value={`${outOfStock} productos`}
                    icon={AlertTriangle}
                    className={outOfStock > 0 ? "border-rose-500/20" : ""}
                />
            </div>

            <DataTable
                columns={columns}
                data={products}
                isLoading={loading}
                searchKey="name"
                searchPlaceholder="Buscar producto o SKU..."
                facetedFilters={[{ column: "status", title: "Estado", options: statusFilterOptions }]}
                emptyMessage="Sin productos encontrados."
                pageSize={20}
            />

            {/* Expanded movements panel rendered outside table */}
            {expandedId && (
                <MovementsPanel
                    productId={expandedId}
                    movements={movements}
                    movementsLoading={movementsLoading}
                />
            )}

            {/* Movement modal */}
            <Dialog open={showModal} onOpenChange={setShowModal}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>Registrar movimiento</DialogTitle>
                        {selectedProduct && (
                            <DialogDescription>
                                {selectedProduct.name} &middot; Stock actual: <span className="text-foreground font-mono">{fmt(selectedProduct.stock_quantity)}</span>
                            </DialogDescription>
                        )}
                    </DialogHeader>
                    {selectedProduct && (
                        <form onSubmit={handleMovement} className="space-y-4">
                            <div>
                                <Label className="text-xs mb-1.5">Tipo de movimiento</Label>
                                <div className="grid grid-cols-3 gap-2 mt-1.5">
                                    {(["entrada", "salida", "ajuste"] as const).map(type => (
                                        <Button
                                            key={type}
                                            type="button"
                                            variant={movForm.movement_type === type ? "default" : "outline"}
                                            onClick={() => setMovForm(f => ({ ...f, movement_type: type }))}
                                            className={`capitalize ${movForm.movement_type === type
                                                ? type === "entrada" ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/30"
                                                    : type === "salida" ? "bg-rose-500/20 border-rose-500/40 text-rose-400 hover:bg-rose-500/30"
                                                        : "bg-amber-500/20 border-amber-500/40 text-amber-400 hover:bg-amber-500/30"
                                                : ""
                                                }`}
                                        >
                                            {type}
                                        </Button>
                                    ))}
                                </div>
                            </div>
                            <div>
                                <Label className="text-xs">
                                    {movForm.movement_type === "ajuste" ? "Nuevo stock total" : "Cantidad"}
                                </Label>
                                <Input
                                    type="number" required min={1} value={movForm.quantity}
                                    onChange={e => setMovForm(f => ({ ...f, quantity: parseInt(e.target.value) || 0 }))}
                                    className="mt-1.5"
                                />
                                {movForm.movement_type !== "ajuste" && (
                                    <p className="text-xs text-muted-foreground mt-1">
                                        Nuevo stock: <span className="text-foreground font-mono">
                                            {movForm.movement_type === "entrada"
                                                ? fmt(selectedProduct.stock_quantity + (movForm.quantity || 0))
                                                : fmt(Math.max(0, selectedProduct.stock_quantity - (movForm.quantity || 0)))}
                                        </span>
                                    </p>
                                )}
                            </div>
                            <div>
                                <Label className="text-xs">Referencia (n\u00ba albar\u00e1n, factura...)</Label>
                                <Input
                                    type="text" value={movForm.reference}
                                    onChange={e => setMovForm(f => ({ ...f, reference: e.target.value }))}
                                    placeholder="ALB-2026-001"
                                    className="mt-1.5"
                                />
                            </div>
                            <div>
                                <Label className="text-xs">Notas</Label>
                                <textarea
                                    value={movForm.notes} rows={2}
                                    onChange={e => setMovForm(f => ({ ...f, notes: e.target.value }))}
                                    className="mt-1.5 w-full bg-background border border-border text-foreground text-sm rounded-md px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-ring transition-colors resize-none"
                                    placeholder="Motivo del ajuste, devoluci\u00f3n, etc."
                                />
                            </div>
                            <DialogFooter>
                                <Button type="button" variant="outline" onClick={() => setShowModal(false)}>
                                    Cancelar
                                </Button>
                                <Button type="submit" disabled={saving}>
                                    {saving && <Loader2 className="mr-2 w-4 h-4 animate-spin" />}
                                    Registrar
                                </Button>
                            </DialogFooter>
                        </form>
                    )}
                </DialogContent>
            </Dialog>

            {/* Product create/edit modal */}
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

// --- Product create/edit dialog extracted ---
function ProductModal({ open, onOpenChange, editingProduct, productForm, setProductForm, onSubmit, saving }: {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    editingProduct: Product | null;
    productForm: ProductForm;
    setProductForm: React.Dispatch<React.SetStateAction<ProductForm>>;
    onSubmit: (e: React.FormEvent) => void;
    saving: boolean;
}) {
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle>
                        {editingProduct ? "Editar producto" : "Nuevo producto"}
                    </DialogTitle>
                </DialogHeader>
                <form onSubmit={onSubmit} className="space-y-4">
                    <div>
                        <Label className="text-xs">Nombre *</Label>
                        <Input
                            type="text"
                            required
                            value={productForm.name}
                            onChange={e => setProductForm(f => ({ ...f, name: e.target.value }))}
                            placeholder="Nombre del producto"
                            className="mt-1.5"
                        />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <Label className="text-xs">SKU</Label>
                            <Input
                                type="text"
                                value={productForm.sku}
                                onChange={e => setProductForm(f => ({ ...f, sku: e.target.value }))}
                                placeholder="SKU-001"
                                className="mt-1.5"
                            />
                        </div>
                        <div>
                            <Label className="text-xs">Precio</Label>
                            <Input
                                type="number"
                                min={0}
                                step={0.01}
                                value={productForm.price}
                                onChange={e => setProductForm(f => ({ ...f, price: parseFloat(e.target.value) || 0 }))}
                                className="mt-1.5"
                            />
                        </div>
                    </div>
                    <div>
                        <Label className="text-xs">Alerta stock m\u00ednimo</Label>
                        <Input
                            type="number"
                            min={0}
                            value={productForm.stock_min_alert}
                            onChange={e => setProductForm(f => ({ ...f, stock_min_alert: parseInt(e.target.value) || 0 }))}
                            className="mt-1.5"
                        />
                    </div>
                    <div>
                        <Label className="text-xs">Descripci\u00f3n</Label>
                        <textarea
                            value={productForm.description}
                            rows={2}
                            onChange={e => setProductForm(f => ({ ...f, description: e.target.value }))}
                            className="mt-1.5 w-full bg-background border border-border text-foreground text-sm rounded-md px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-ring transition-colors resize-none"
                            placeholder="Descripci\u00f3n opcional"
                        />
                    </div>
                    <DialogFooter>
                        <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                            Cancelar
                        </Button>
                        <Button type="submit" disabled={saving}>
                            {saving && <Loader2 className="mr-2 w-4 h-4 animate-spin" />}
                            {editingProduct ? "Guardar cambios" : "Crear producto"}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
