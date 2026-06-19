"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { api, type Product, type StockMovement } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import { useConfirmStore } from "@/stores/confirm";
import { logError } from "@/lib/logger";

export interface MovementForm {
    movement_type: "entrada" | "salida" | "ajuste";
    quantity: number;
    reference: string;
    notes: string;
}

export interface ProductForm {
    name: string;
    sku: string;
    barcode: string;
    category: string;
    location: string;
    unit: string;
    price: number;
    cost_price: number | null;
    stock_min_alert: number;
    description: string;
    is_active: boolean;
    supplier_id: string | null;
    reorder_quantity: number | null;
}

const emptyProductForm: ProductForm = {
    name: "", sku: "", barcode: "", category: "", location: "", unit: "ud",
    price: 0, cost_price: null, stock_min_alert: 0,
    description: "", is_active: true, supplier_id: null, reorder_quantity: null,
};

export function useStock() {
    const t = useTranslations("inventario");
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

    const [showProductModal, setShowProductModal] = useState(false);
    const [editingProduct, setEditingProduct] = useState<Product | null>(null);
    const [productForm, setProductForm] = useState<ProductForm>(emptyProductForm);
    const [savingProduct, setSavingProduct] = useState(false);

    const [editingAlertId, setEditingAlertId] = useState<string | null>(null);
    const [alertValue, setAlertValue] = useState(0);
    const alertInputRef = useRef<HTMLInputElement>(null);

    const [query, setQuery] = useState("");
    const [categoryFilter, setCategoryFilter] = useState("");
    const [debouncedQuery, setDebouncedQuery] = useState("");

    useEffect(() => {
        const t = setTimeout(() => setDebouncedQuery(query.trim()), 300);
        return () => clearTimeout(t);
    }, [query]);

    const load = useCallback(() => {
        setLoading(true);
        return api.erp.products.list({
            limit: 200,
            q: debouncedQuery || undefined,
            category: categoryFilter || undefined,
        })
            .then(data => setProducts(data.filter(p => p.item_type === "product")))
            .catch(err => logError("inventario/stock/page", err))
            .finally(() => setLoading(false));
    }, [debouncedQuery, categoryFilter]);

    useEffect(() => { load(); }, [load]);

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
            toast.error(err?.message || t("stock.movementError"));
        } finally {
            setSaving(false);
        }
    };

    const startEditAlert = (product: Product) => {
        setEditingAlertId(product.id);
        setAlertValue(product.stock_min_alert);
    };

    const saveAlert = async (productId: string) => {
        setEditingAlertId(null);
        try {
            await api.erp.products.update(productId, { stock_min_alert: alertValue });
            load();
            toast.success(t("stock.alertUpdated"));
        } catch (err: any) {
            toast.error(err?.message || t("stock.alertUpdateError"));
        }
    };

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
            barcode: product.barcode || "",
            category: product.category || "",
            location: product.location || "",
            unit: product.unit || "ud",
            price: product.price,
            cost_price: product.cost_price,
            stock_min_alert: product.stock_min_alert,
            description: product.description || "",
            is_active: product.is_active,
            supplier_id: product.supplier_id ?? null,
            reorder_quantity: product.reorder_quantity ?? null,
        });
        setShowProductModal(true);
    };

    const handleProductSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSavingProduct(true);
        const payload = {
            ...productForm,
            sku: productForm.sku || null,
            barcode: productForm.barcode || null,
            category: productForm.category || null,
            location: productForm.location || null,
            description: productForm.description || null,
            supplier_id: productForm.supplier_id || null,
        };
        try {
            if (editingProduct) {
                await api.erp.products.update(editingProduct.id, payload);
                toast.success(t("stock.productUpdated"));
            } else {
                await api.erp.products.create({ ...payload, item_type: "product" });
                toast.success(t("stock.productCreated"));
            }
            setShowProductModal(false);
            load();
        } catch (err: any) {
            toast.error(err?.message || t("stock.productSaveError"));
        } finally {
            setSavingProduct(false);
        }
    };

    const handleDelete = async (product: Product) => {
        const ok = await confirm.show({
            title: t("stock.deleteTitle"),
            message: t("stock.deleteMessage", { name: product.name }),
            confirmLabel: t("stock.deleteConfirm"),
            confirmVariant: "danger",
        });
        if (!ok) return;
        try {
            await api.erp.products.delete(product.id);
            toast.success(t("stock.productDeleted"));
            load();
        } catch (err: any) {
            toast.error(err?.message || t("stock.productDeleteError"));
        }
    };

    return {
        products, loading, expandedId, movements, movementsLoading,
        showModal, setShowModal, selectedProduct, setSelectedProduct,
        movForm, setMovForm, saving,
        showProductModal, setShowProductModal, editingProduct, setEditingProduct,
        productForm, setProductForm, savingProduct,
        editingAlertId, setEditingAlertId, alertValue, setAlertValue,
        alertInputRef,
        query, setQuery, categoryFilter, setCategoryFilter,
        handleMovement, handleProductSubmit, handleDelete, load,
        toggleExpand, openMovement, openCreateProduct, openEditProduct,
        startEditAlert, saveAlert,
    };
}
