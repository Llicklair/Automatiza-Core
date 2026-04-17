"use client";

import { Loader2 } from "lucide-react";
import { type Product } from "@/lib/api";
import { type ProductForm } from "../_hooks/useStock";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";

interface ProductModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    editingProduct: Product | null;
    productForm: ProductForm;
    setProductForm: React.Dispatch<React.SetStateAction<ProductForm>>;
    onSubmit: (e: React.FormEvent) => void;
    saving: boolean;
}

export function ProductModal({ open, onOpenChange, editingProduct, productForm, setProductForm, onSubmit, saving }: ProductModalProps) {
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
                        <Label className="text-xs">Alerta stock mínimo</Label>
                        <Input
                            type="number"
                            min={0}
                            value={productForm.stock_min_alert}
                            onChange={e => setProductForm(f => ({ ...f, stock_min_alert: parseInt(e.target.value) || 0 }))}
                            className="mt-1.5"
                        />
                    </div>
                    <div>
                        <Label className="text-xs">Descripción</Label>
                        <textarea
                            value={productForm.description}
                            rows={2}
                            onChange={e => setProductForm(f => ({ ...f, description: e.target.value }))}
                            className="mt-1.5 w-full bg-background border border-border text-foreground text-sm rounded-md px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-ring transition-colors resize-none"
                            placeholder="Descripción opcional"
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
