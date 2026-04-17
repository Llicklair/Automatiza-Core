"use client";

import { Package, DollarSign, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { X } from "lucide-react";

type FormState = {
    name: string; sku: string; description: string;
    price: string; tax_percentage: string; item_type: string;
};

interface Props {
    editingId: string | null;
    form: FormState;
    onChange: (f: FormState) => void;
    onSubmit: (e: React.FormEvent) => void;
    onClose: () => void;
    isSubmitting: boolean;
}

export function ProductModal({ editingId, form, onChange, onSubmit, onClose, isSubmitting }: Props) {
    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-card border border-border rounded-2xl w-full max-w-xl overflow-hidden shadow-2xl">
                <div className="p-5 border-b border-border flex justify-between items-center bg-muted">
                    <h2 className="text-lg font-medium text-foreground flex items-center gap-2">
                        <Package className="w-4 h-4 text-primary" />
                        {editingId ? "Editar Artículo" : "Nuevo Artículo"}
                    </h2>
                    <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onClose}>
                        <X className="h-5 w-5" />
                    </Button>
                </div>

                <form onSubmit={onSubmit} className="p-6 space-y-5">
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">Nombre *</label>
                            <input
                                type="text"
                                required
                                value={form.name}
                                onChange={e => onChange({ ...form, name: e.target.value })}
                                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary transition-colors"
                            />
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">SKU / Ref.</label>
                            <input
                                type="text"
                                value={form.sku}
                                onChange={e => onChange({ ...form, sku: e.target.value })}
                                placeholder="Opcional"
                                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary font-mono text-sm transition-colors"
                            />
                        </div>
                    </div>
                    <div>
                        <label className="block text-sm text-muted-foreground mb-1.5">Descripción</label>
                        <textarea
                            value={form.description}
                            onChange={e => onChange({ ...form, description: e.target.value })}
                            className="w-full bg-background border border-border rounded-lg px-4 py-2 text-foreground focus:outline-none focus:border-primary resize-none h-20 transition-colors"
                        />
                    </div>
                    <div className="grid grid-cols-3 gap-4 border-t border-border pt-4">
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">Naturaleza</label>
                            <select
                                value={form.item_type}
                                onChange={e => onChange({ ...form, item_type: e.target.value })}
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
                                    onChange={e => onChange({ ...form, price: e.target.value })}
                                    className="w-full bg-background border border-border rounded-lg pl-9 pr-3 py-2 text-foreground focus:outline-none focus:border-primary transition-colors"
                                />
                            </div>
                        </div>
                        <div>
                            <label className="block text-sm text-muted-foreground mb-1.5">% IVA</label>
                            <select
                                value={form.tax_percentage}
                                onChange={e => onChange({ ...form, tax_percentage: e.target.value })}
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
                        <Button type="button" variant="outline" onClick={onClose}>
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
    );
}
