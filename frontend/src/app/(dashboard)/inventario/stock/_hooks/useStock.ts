"use client";

import { useEffect, useState, useRef } from "react";
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
    price: number;
    stock_min_alert: number;
    description: string;
}

const emptyProductForm: ProductForm = { name: "", sku: "", price: 0, stock_min_alert: 0, description: "" };

export function useStock() {
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

    const load = () =>
        api.erp.products.list({ limit: 200 })
            .then(data => setProducts(data.filter(p => p.item_type === "product")))
            .catch(err => logError("inventario/stock/page", err))
            .finally(() => setLoading(false));

    useEffect(() => { load(); }, []);

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

    const startEditAlert = (product: Product) => {
        setEditingAlertId(product.id);
        setAlertValue(product.stock_min_alert);
    };

    const saveAlert = async (productId: string) => {
        setEditingAlertId(null);
        try {
            await api.erp.products.update(productId, { stock_min_alert: alertValue });
            load();
            toast.success("Alerta mínima actualizada");
        } catch (err: any) {
            toast.error(err?.message || "Error al actualizar alerta");
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

    const handleDelete = async (product: Product) => {
        const ok = await confirm.show({
            title: "Eliminar producto",
            message: `Se eliminará "${product.name}" permanentemente. Esta acción no se puede deshacer.`,
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

    return {
        products, loading, expandedId, movements, movementsLoading,
        showModal, setShowModal, selectedProduct, setSelectedProduct,
        movForm, setMovForm, saving,
        showProductModal, setShowProductModal, editingProduct, setEditingProduct,
        productForm, setProductForm, savingProduct,
        editingAlertId, setEditingAlertId, alertValue, setAlertValue,
        alertInputRef,
        handleMovement, handleProductSubmit, handleDelete, load,
        toggleExpand, openMovement, openCreateProduct, openEditProduct,
        startEditAlert, saveAlert,
    };
}
