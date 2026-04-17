"use client";

import { Loader2 } from "lucide-react";
import { type Product } from "@/lib/api";
import { type MovementForm } from "../_hooks/useStock";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";

const fmt = (n: number) => n.toLocaleString("es-ES");

interface MovementModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    selectedProduct: Product | null;
    movForm: MovementForm;
    setMovForm: React.Dispatch<React.SetStateAction<MovementForm>>;
    onSubmit: (e: React.FormEvent) => void;
    saving: boolean;
}

export function MovementModal({ open, onOpenChange, selectedProduct, movForm, setMovForm, onSubmit, saving }: MovementModalProps) {
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
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
                    <form onSubmit={onSubmit} className="space-y-4">
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
                            <Label className="text-xs">Referencia (nº albarán, factura...)</Label>
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
                                placeholder="Motivo del ajuste, devolución, etc."
                            />
                        </div>
                        <DialogFooter>
                            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
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
    );
}
